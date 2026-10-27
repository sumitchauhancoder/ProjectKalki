import asyncio
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
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
from llm_engine import process_jarvis_intent
from tts_engine import speak_text

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[Database Init Warning]: PostgreSQL unavailable ({e}). Continuing with graceful fallback.")

app = FastAPI(title="KALKI Core Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recognizer = sr.Recognizer()

class CommandPayload(BaseModel):
    command: str

class FramePayload(BaseModel):
    image_base64: str

class MacroCreatePayload(BaseModel):
    trigger_phrase: str
    action_type: str
    action_payload: Dict[str, Any]

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
async def run_command(payload: CommandPayload, db: Optional[Session] = Depends(get_db)):
    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Empty command input")

    matched_macro = None
    try:
        if db is not None:
            matched_macro = db.query(models.VoiceMacro).filter(
                models.VoiceMacro.trigger_phrase == cmd.lower()
            ).first()
    except Exception as db_err:
        print(f"[Database Warning]: {db_err}")

    if matched_macro:
        executed_info = execute_macro_action(matched_macro)
        reply_message = f"Executing stored macro '{matched_macro.trigger_phrase}'"
    else:
        llm_res = await asyncio.to_thread(process_jarvis_intent, cmd)
        reply_message = llm_res.get("reply", "Command completed.")
        executed_info = llm_res.get("tool_executed")

    # Non-blocking TTS (runs in background without freezing UI or delaying HTTP response)
    asyncio.create_task(speak_text(reply_message))

    try:
        if db is not None:
            log_entry = models.AuditLog(
                command_input=cmd,
                execution_status="success" if executed_info else "reasoned",
                telemetry_data={"response": reply_message, "executed": executed_info}
            )
            db.add(log_entry)
            db.commit()
    except Exception as db_err:
        print(f"[Audit Log Warning]: {db_err}")

    return {
        "status": "success",
        "reply": reply_message,
        "executed": executed_info or "Command processed"
    }

@app.post("/listen-voice")
async def listen_voice(db: Optional[Session] = Depends(get_db)):
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

        matched_macro = None
        try:
            if db is not None:
                matched_macro = db.query(models.VoiceMacro).filter(
                    models.VoiceMacro.trigger_phrase == transcript.lower()
                ).first()
        except Exception as db_err:
            print(f"[Database Warning]: {db_err}")

        if matched_macro:
            executed_info = execute_macro_action(matched_macro)
            reply_message = f"Executing macro '{matched_macro.trigger_phrase}'"
        else:
            llm_res = await asyncio.to_thread(process_jarvis_intent, transcript)
            reply_message = llm_res.get("reply", "Speech processed.")
            executed_info = llm_res.get("tool_executed")

        # Non-blocking background TTS
        asyncio.create_task(speak_text(reply_message))

        try:
            if db is not None:
                log_entry = models.AuditLog(
                    command_input=transcript,
                    execution_status="success" if executed_info else "reasoned",
                    telemetry_data={"response": reply_message, "executed": executed_info}
                )
                db.add(log_entry)
                db.commit()
        except Exception as db_err:
            print(f"[Audit Log Warning]: {db_err}")

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
def create_macro(payload: MacroCreatePayload, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database currently unavailable.")
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/macros")
def list_macros(db: Optional[Session] = Depends(get_db)):
    if db is None:
        return []
    try:
        return db.query(models.VoiceMacro).all()
    except Exception:
        return []

@app.get("/audit-logs")
def get_audit_logs(limit: int = 15, db: Optional[Session] = Depends(get_db)):
    if db is None:
        return []
    try:
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
    except Exception:
        return []

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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
