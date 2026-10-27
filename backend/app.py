import asyncio
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any
import uvicorn
import cv2
import numpy as np
import base64
import sounddevice as sd
import speech_recognition as sr
import wave
import io
import subprocess
import pyautogui

from database import Base, engine, get_db
import models
from llm_engine import process_jarvis_intent, click_bounding_box, click_at_coordinates
from tts_engine import speak_text
from auth import auth_router

# 1. Initialize FastAPI app first
app = FastAPI(title="KALKI Core Engine", version="1.0.0")

# 2. Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Include Auth Router and create database tables
app.include_router(auth_router)
Base.metadata.create_all(bind=engine)

recognizer = sr.Recognizer()

class CommandPayload(BaseModel):
    command: str

class FramePayload(BaseModel):
    image_base64: str

class MacroCreatePayload(BaseModel):
    trigger_phrase: str
    action_type: str
    action_payload: Dict[str, Any]

class VisualClickPayload(BaseModel):
    box_index: int
    bounding_boxes: list

def execute_macro_action(macro: models.VoiceMacro) -> str:
    action_type = macro.action_type
    payload = macro.action_payload

    if action_type == "launch_app":
        app_path = payload.get("path")
        if app_path:
            subprocess.Popen(app_path, shell=True)
            return f"Launched process: {app_path}"
    elif action_type == "hotkey":
        keys = payload.get("keys", [])
        if keys:
            pyautogui.hotkey(*keys)
            return f"Executed hotkey: {'+'.join(keys)}"
    elif action_type == "type_text":
        text = payload.get("text", "")
        if text:
            pyautogui.write(text, interval=0.01)
            return f"Typed text: {text.strip()}"
    return "Executed macro"

@app.get("/")
def health_check():
    return {"status": "online", "system": "KALKI Jarvis Core Engine"}

@app.post("/execute-command")
async def run_command(payload: CommandPayload, db: Session = Depends(get_db)):
    try:
        cmd = payload.command.strip()
        if not cmd:
            raise HTTPException(status_code=400, detail="Empty command input")

        active_session = db.query(models.ChatSession).filter(models.ChatSession.id == 1).first()
        if not active_session:
            active_session = models.ChatSession(id=1, session_title="KALKI Core Session")
            db.add(active_session)
            db.commit()

        past_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == 1
        ).order_by(models.ChatMessage.timestamp.asc()).all()
        
        history_context = [{"role": m.role, "content": m.content} for m in past_messages[-10:]]

        user_msg_db = models.ChatMessage(session_id=1, role="user", content=cmd)
        db.add(user_msg_db)
        db.commit()

        executed_info = None
        reply_message = ""

        matched_macro = db.query(models.VoiceMacro).filter(
            models.VoiceMacro.trigger_phrase == cmd.lower()
        ).first()

        if matched_macro:
            executed_info = execute_macro_action(matched_macro)
            reply_message = f"Executing stored macro '{matched_macro.trigger_phrase}'"
        else:
            llm_res = process_jarvis_intent(cmd, chat_history=history_context)
            reply_message = llm_res.get("reply", "Command completed.")
            executed_info = llm_res.get("tool_executed")

        assistant_msg_db = models.ChatMessage(session_id=1, role="assistant", content=reply_message)
        db.add(assistant_msg_db)
        db.commit()

        try:
            asyncio.create_task(speak_text(reply_message))
        except Exception as tts_err:
            print(f"[TTS Background Error]: {tts_err}")

        log_entry = models.AuditLog(
            command_input=cmd,
            execution_status="success" if executed_info else "reasoned",
            telemetry_data=json.dumps({"response": reply_message, "executed": executed_info})
        )
        db.add(log_entry)
        db.commit()

        return {
            "status": "success",
            "reply": reply_message,
            "executed": executed_info or "Command processed"
        }

    except Exception as e:
        db.rollback()
        print(f"[Execution Error]: {str(e)}")
        return {
            "status": "error",
            "reply": f"Core Error: {str(e)}",
            "executed": None
        }

@app.post("/listen-voice")
async def listen_voice(db: Session = Depends(get_db)):
    try:
        sample_rate = 16000
        duration = 4

        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()

        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(recording.tobytes())
        wav_io.seek(0)

        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            try:
                transcript = recognizer.recognize_google(audio_data, language="kn-IN").strip()
            except Exception:
                transcript = recognizer.recognize_google(audio_data, language="en-IN").strip()

        matched_macro = db.query(models.VoiceMacro).filter(
            models.VoiceMacro.trigger_phrase == transcript.lower()
        ).first()

        if matched_macro:
            executed_info = execute_macro_action(matched_macro)
            reply_message = f"Executing macro '{matched_macro.trigger_phrase}'"
        else:
            llm_res = process_jarvis_intent(transcript)
            reply_message = llm_res.get("reply", "Speech processed.")
            executed_info = llm_res.get("tool_executed")

        asyncio.create_task(speak_text(reply_message))

        log_entry = models.AuditLog(
            command_input=transcript,
            execution_status="success" if executed_info else "reasoned",
            telemetry_data=json.dumps({"response": reply_message, "executed": executed_info})
        )
        db.add(log_entry)
        db.commit()

        return {
            "status": "success",
            "transcript": transcript,
            "reply": reply_message,
            "executed": executed_info or "Speech processed"
        }

    except sr.UnknownValueError:
        msg = "Could not decipher speech audio."
        asyncio.create_task(speak_text(msg))
        return {"status": "unclear", "transcript": "", "reply": msg, "executed": None}
    except Exception as e:
        return {"status": "error", "transcript": "", "reply": str(e), "executed": None}

@app.post("/macros")
def create_macro(payload: MacroCreatePayload, db: Session = Depends(get_db)):
    existing = db.query(models.VoiceMacro).filter(
        models.VoiceMacro.trigger_phrase == payload.trigger_phrase.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Trigger phrase already exists.")

    new_macro = models.VoiceMacro(
        trigger_phrase=payload.trigger_phrase.lower(),
        action_type=payload.action_type,
        action_payload=payload.action_payload
    )
    db.add(new_macro)
    db.commit()
    db.refresh(new_macro)
    return {"status": "success", "trigger": new_macro.trigger_phrase, "macro_id": new_macro.id}

@app.get("/macros")
def list_macros(db: Session = Depends(get_db)):
    return db.query(models.VoiceMacro).all()

@app.get("/audit-logs")
def get_audit_logs(limit: int = 15, db: Session = Depends(get_db)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "command_input": log.command_input,
            "execution_status": log.execution_status,
            "telemetry_data": log.telemetry_data,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]

@app.get("/chat-history")
def get_chat_history(db: Session = Depends(get_db)):
    messages = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == 1).order_by(models.ChatMessage.timestamp.asc()).all()
    return [{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in messages]

@app.post("/process-frame")
async def process_frame(payload: FramePayload):
    try:
        encoded_data = payload.image_base64
        if "," in encoded_data:
            encoded_data = encoded_data.split(",")[1]

        img_bytes = base64.b64decode(encoded_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid frame data")

        img_h, img_w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        ui_elements = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            if 80 < area < (img_w * img_h * 0.85) and w > 15 and h > 15:
                ui_elements.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": int(area)})

        unique_elements = []
        seen = set()
        for box in sorted(ui_elements, key=lambda b: b["area"], reverse=True):
            spatial_key = (box["x"] // 15, box["y"] // 15, box["w"] // 15, box["h"] // 15)
            if spatial_key not in seen:
                seen.add(spatial_key)
                unique_elements.append(box)

        return {
            "status": "success",
            "frame_dimensions": {"width": img_w, "height": img_h},
            "detected_ui_bounding_boxes": len(unique_elements),
            "sample_boxes": unique_elements[:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/visual-click")
async def visual_click(payload: VisualClickPayload, db: Session = Depends(get_db)):
    try:
        result_msg = click_bounding_box(payload.box_index, payload.bounding_boxes)
        asyncio.create_task(speak_text(result_msg))

        log_entry = models.AuditLog(
            command_input=f"Visual Click Box #{payload.box_index}",
            execution_status="success",
            telemetry_data=json.dumps({"action": "visual_click", "result": result_msg})
        )
        db.add(log_entry)
        db.commit()

        return {"status": "success", "reply": result_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)