import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
import base64
import cv2
import io
import json
import os
import numpy as np
import re
import time
from typing import Dict, Any, Optional
import pyautogui
import sounddevice as sd
import speech_recognition as sr
import subprocess
import uvicorn
import wave
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
from llm_engine import (
    process_jarvis_intent,
    process_jarvis_intent_stream,
    click_bounding_box,
    click_at_coordinates,
    detect_reply_language,
)
import tts_engine
from tts_engine import speak_text
from sentence_splitter import SentenceSplitter
from auth import auth_router, get_current_user
from admin import admin_router
from settings import load_settings, save_settings

app = FastAPI(title="KALKI Core Engine", version="1.0.0")

# CORS configuration targeting Vite dev server origins
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)

# Safe database initialization: do not crash on startup if DB is offline
try:
    Base.metadata.create_all(bind=engine)
    # Lightweight schema migration for existing databases
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            is_postgres = "postgres" in str(engine.url)
            for col, col_def in [
                ("role", "VARCHAR DEFAULT 'user'"),
                ("status", "VARCHAR DEFAULT 'active'"),
                ("last_login", "TIMESTAMP" if is_postgres else "DATETIME")
            ]:
                try:
                    if is_postgres:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_def}"))
                    else:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_def}"))
                    conn.commit()
                except Exception:
                    pass
    except Exception:
        pass
except Exception as e:
    print(f"[Database Warning] Table initialization skipped: {type(e).__name__}")

recognizer = sr.Recognizer()

def recognize_speech(audio_data, language: str = "en-IN") -> str:
    """
    Recognizes speech using the specified language.
    Default language: en-IN.
    If en-IN fails (UnknownValueError or empty), retries once with en-US.
    For other languages (e.g. kn-IN, hi-IN), uses that language directly without falling back to Kannada for English.
    """
    if language == "en-IN" or (isinstance(language, str) and language.startswith("en")):
        try:
            transcript = recognizer.recognize_google(audio_data, language="en-IN").strip()
            if transcript:
                return transcript
        except (sr.UnknownValueError, Exception):
            pass
        # Retry once with en-US if en-IN was empty or raised an exception
        return recognizer.recognize_google(audio_data, language="en-US").strip()
    else:
        return recognizer.recognize_google(audio_data, language=language).strip()

class CommandPayload(BaseModel):
    command: str

class FramePayload(BaseModel):
    image_base64: str

class MacroCreatePayload(BaseModel):
    trigger_phrase: str
    action_type: str
    action_payload: str

class VisualClickPayload(BaseModel):
    box_index: int
    bounding_boxes: list

def execute_macro_action(macro: models.VoiceMacro) -> str:
    action_type = macro.action_type
    try:
        payload = json.loads(macro.action_payload) if isinstance(macro.action_payload, str) else macro.action_payload
    except Exception:
        payload = {"path": macro.action_payload, "keys": [macro.action_payload], "text": macro.action_payload}

    if action_type == "launch_app":
        app_path = payload.get("path") if isinstance(payload, dict) else str(payload)
        if app_path:
            subprocess.Popen(app_path, shell=True)
            return f"Launched process: {app_path}"
    elif action_type == "hotkey":
        keys = payload.get("keys", []) if isinstance(payload, dict) else [str(payload)]
        if keys:
            pyautogui.hotkey(*keys)
            return f"Executed hotkey: {'+'.join(keys)}"
    elif action_type == "type_text":
        text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
        if text:
            pyautogui.write(text, interval=0.01)
            return f"Typed text: {text.strip()}"
    return "Executed macro"

@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "online", "system": "KALKI Jarvis Core Engine"}

@app.get("/settings")
def get_user_settings():
    return load_settings()

@app.post("/settings")
def update_user_settings(payload: Dict[str, Any]):
    updated = save_settings(payload)
    return {"status": "success", "settings": updated}

STOP_WORDS = {
    "stop", "cancel", "halt", "quiet", "shut up",
    "रुको", "रुकिए", "बंद करो", "बस", "roko", "band karo", "bas",
    "ನಿಲ್ಲಿಸು", "ಸಾಕು", "ಶಾಂತವಾಗಿರಿ", "nillisu", "saaku"
}

def is_stop_command(text: str) -> bool:
    if not text:
        return False
    cleaned = text.strip().lower().strip(".,!?:;\"' \t\n\r")
    return cleaned in STOP_WORDS

active_cancel_event: Optional[asyncio.Event] = None

def cancel_active_pipeline():
    """Cancels active streaming generation and stops persistent TTS audio playback."""
    global active_cancel_event
    if active_cancel_event is not None:
        active_cancel_event.set()
    tts_engine.cancel_playback_and_queue()

@app.post("/stop")
def stop_all():
    """Cancels active speech, generation, and clears queued audio within ~300ms."""
    cancel_active_pipeline()
    return {"status": "stopped", "message": "Speech and generation stopped."}

@app.post("/execute-command")
async def run_command(payload: CommandPayload, db: Optional[Session] = Depends(get_db)):
    t_start = time.perf_counter()
    cancel_active_pipeline()
    tts_engine.reset_cancel()
    global active_cancel_event
    active_cancel_event = asyncio.Event()

    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Empty command input")

    if is_stop_command(cmd):
        cancel_active_pipeline()
        return {
            "status": "cancelled",
            "reply": "Stopped.",
            "executed": "User interruption"
        }

    history_context = []
    matched_macro = None

    # Database read operations are safe; if DB is unreachable, continue gracefully
    if db is not None:
        try:
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

            matched_macro = db.query(models.VoiceMacro).filter(
                models.VoiceMacro.trigger_phrase == cmd.lower()
            ).first()
        except Exception as db_err:
            print(f"[Database Warning]: Failed query in /execute-command: {type(db_err).__name__}")
            try:
                db.rollback()
            except Exception:
                pass

    if matched_macro:
        executed_info = execute_macro_action(matched_macro)
        reply_message = f"Executing stored macro '{matched_macro.trigger_phrase}'"
    else:
        # Offload blocking LLM SDK calls to a background thread
        t_llm_start = time.perf_counter()
        llm_res = await asyncio.to_thread(process_jarvis_intent, cmd, chat_history=history_context)
        t_llm_end = time.perf_counter()
        llm_ms = (t_llm_end - t_llm_start) * 1000
        if os.getenv("DEBUG_TIMING", "0") == "1":
            print(f"[TIMING] LLM call time: {llm_ms:.1f}ms", flush=True)
        reply_message = llm_res.get("reply", "Command completed.")
        executed_info = llm_res.get("tool_executed")

    # Database write operations
    if db is not None:
        try:
            assistant_msg_db = models.ChatMessage(session_id=1, role="assistant", content=reply_message)
            db.add(assistant_msg_db)
            log_entry = models.AuditLog(
                command_input=cmd,
                execution_status="success" if executed_info else "reasoned",
                telemetry_data=json.dumps({"response": reply_message, "executed": executed_info})
            )
            db.add(log_entry)
            db.commit()
        except Exception as db_err:
            print(f"[Database Warning]: Failed commit in /execute-command: {type(db_err).__name__}")
            try:
                db.rollback()
            except Exception:
                pass

    # Non-blocking background TTS
    try:
        asyncio.create_task(speak_text(reply_message, request_start_time=t_start))
    except Exception as tts_err:
        print(f"[TTS Background Error]: {tts_err}")

    if os.getenv("DEBUG_TIMING", "0") == "1":
        total_ms = (time.perf_counter() - t_start) * 1000
        print(f"[TIMING] Total time: {total_ms:.1f}ms", flush=True)

    return {
        "status": "success",
        "reply": reply_message,
        "executed": executed_info or "Command processed"
    }

@app.post("/chat-stream")
async def chat_stream(payload: CommandPayload, db: Optional[Session] = Depends(get_db)):
    t_start = time.perf_counter()
    cancel_active_pipeline()
    tts_engine.reset_cancel()
    global active_cancel_event
    active_cancel_event = asyncio.Event()
    current_cancel = active_cancel_event

    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Empty command input")

    if is_stop_command(cmd):
        cancel_active_pipeline()
        async def stop_gen():
            yield f"event: token\ndata: {json.dumps({'text': 'Stopped.'})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'done'})}\n\n"
        return StreamingResponse(stop_gen(), media_type="text/event-stream")

    history_context = []
    matched_macro = None

    if db is not None:
        try:
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

            matched_macro = db.query(models.VoiceMacro).filter(
                models.VoiceMacro.trigger_phrase == cmd.lower()
            ).first()
        except Exception as db_err:
            print(f"[Database Warning]: Failed query in /chat-stream: {type(db_err).__name__}")
            try:
                db.rollback()
            except Exception:
                pass

    async def event_generator():
        splitter = SentenceSplitter()
        accumulated_sentences = []

        if matched_macro:
            execute_macro_action(matched_macro)
            macro_reply = f"Executing stored macro '{matched_macro.trigger_phrase}'"
            accumulated_sentences.append(macro_reply)
            yield f"event: token\ndata: {json.dumps({'text': macro_reply})}\n\n"
        else:
            async for chunk in process_jarvis_intent_stream(
                cmd, chat_history=history_context, cancel_event=current_cancel, request_start_time=t_start, is_voice=False
            ):
                if current_cancel.is_set():
                    break
                sentences = splitter.feed(chunk)
                for sentence in sentences:
                    if current_cancel.is_set():
                        break
                    accumulated_sentences.append(sentence)
                    yield f"event: token\ndata: {json.dumps({'text': sentence})}\n\n"

            if not current_cancel.is_set():
                for remaining in splitter.flush():
                    if current_cancel.is_set():
                        break
                    accumulated_sentences.append(remaining)
                    yield f"event: token\ndata: {json.dumps({'text': remaining})}\n\n"

        full_reply = " ".join(accumulated_sentences).strip()
        if full_reply and not current_cancel.is_set():
            asyncio.create_task(speak_text(full_reply, request_start_time=t_start))

        if db is not None and full_reply and not current_cancel.is_set():
            try:
                assistant_msg_db = models.ChatMessage(session_id=1, role="assistant", content=full_reply)
                db.add(assistant_msg_db)
                log_entry = models.AuditLog(
                    command_input=cmd,
                    execution_status="success",
                    telemetry_data=json.dumps({"response": full_reply})
                )
                db.add(log_entry)
                db.commit()
            except Exception as db_err:
                print(f"[Database Warning]: Failed commit in /chat-stream: {type(db_err).__name__}")
                try:
                    db.rollback()
                except Exception:
                    pass

        if os.getenv("DEBUG_TIMING", "0") == "1":
            total_ms = (time.perf_counter() - t_start) * 1000
            print(f"[TIMING] Total time: {total_ms:.1f}ms", flush=True)

        yield f"event: done\ndata: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/listen-voice")
async def listen_voice(request: Request, db: Optional[Session] = Depends(get_db)):
    t_start = time.perf_counter()
    cancel_active_pipeline()
    tts_engine.reset_cancel()
    global active_cancel_event
    active_cancel_event = asyncio.Event()
    current_cancel = active_cancel_event

    is_sse = "text/event-stream" in request.headers.get("accept", "") or request.query_params.get("stream") == "true"

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

        user_settings = load_settings()
        user_lang = user_settings.get("language", "en-IN")

        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            transcript = recognize_speech(audio_data, language=user_lang)

        # Language mismatch check: when Voice Lang is Kannada/Hindi and transcript contains only Latin letters, treat input as English
        is_indic_setting = isinstance(user_lang, str) and (user_lang.startswith("kn") or user_lang.startswith("hi"))
        has_indic_chars = bool(re.search(r'[\u0900-\u097F\u0C80-\u0CFF]', transcript))
        has_latin_chars = bool(re.search(r'[a-zA-Z]', transcript))
        if is_indic_setting and has_latin_chars and not has_indic_chars:
            print("[STT] language mismatch, using en-IN", flush=True)

        # Check for spoken stop word
        if is_stop_command(transcript):
            cancel_active_pipeline()
            if not is_sse:
                return {
                    "status": "cancelled",
                    "transcript": transcript,
                    "reply": "Stopped.",
                    "executed": "User interruption"
                }
            async def stop_event_generator():
                yield f"event: transcript\ndata: {json.dumps({'transcript': transcript})}\n\n"
                yield f"event: token\ndata: {json.dumps({'text': 'Stopped.'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'status': 'done'})}\n\n"
            return StreamingResponse(
                stop_event_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )

        matched_macro = None
        if db is not None:
            try:
                matched_macro = db.query(models.VoiceMacro).filter(
                    models.VoiceMacro.trigger_phrase == transcript.lower()
                ).first()
            except Exception as db_err:
                print(f"[Database Warning]: {db_err}")

        # Check if caller wants non-streamed JSON (e.g. tests or explicit non-SSE request)
        if not is_sse:
            if matched_macro:
                executed_info = execute_macro_action(matched_macro)
                reply_message = f"Executing macro '{matched_macro.trigger_phrase}'"
            else:
                llm_res = await asyncio.to_thread(process_jarvis_intent, transcript, None, True)
                reply_message = llm_res.get("reply", "Speech processed.")
                executed_info = llm_res.get("tool_executed")

            asyncio.create_task(speak_text(reply_message, request_start_time=t_start))

            if db is not None:
                try:
                    log_entry = models.AuditLog(
                        command_input=transcript,
                        execution_status="success" if executed_info else "reasoned",
                        telemetry_data=json.dumps({"response": reply_message, "executed": executed_info})
                    )
                    db.add(log_entry)
                    db.commit()
                except Exception as db_err:
                    print(f"[Database Warning]: {db_err}")

            if os.getenv("DEBUG_TIMING", "0") == "1":
                total_ms = (time.perf_counter() - t_start) * 1000
                print(f"[TIMING] Total time: {total_ms:.1f}ms", flush=True)

            return {
                "status": "success",
                "transcript": transcript,
                "reply": reply_message,
                "executed": executed_info or "Speech processed"
            }

        # Streaming voice path: returns transcript immediately, then streams reply as sentences
        async def voice_stream_generator():
            splitter = SentenceSplitter()
            accumulated_sentences = []

            # 1. Immediately yield transcript event
            yield f"event: transcript\ndata: {json.dumps({'transcript': transcript})}\n\n"

            if matched_macro:
                execute_macro_action(matched_macro)
                macro_reply = f"Executing macro '{matched_macro.trigger_phrase}'"
                accumulated_sentences.append(macro_reply)
                yield f"event: token\ndata: {json.dumps({'text': macro_reply})}\n\n"
            else:
                async for chunk in process_jarvis_intent_stream(
                    transcript, cancel_event=current_cancel, request_start_time=t_start, is_voice=True
                ):
                    if current_cancel.is_set():
                        break
                    sentences = splitter.feed(chunk)
                    for sentence in sentences:
                        if current_cancel.is_set():
                            break
                        accumulated_sentences.append(sentence)
                        yield f"event: token\ndata: {json.dumps({'text': sentence})}\n\n"

                if not current_cancel.is_set():
                    for remaining in splitter.flush():
                        if current_cancel.is_set():
                            break
                        accumulated_sentences.append(remaining)
                        yield f"event: token\ndata: {json.dumps({'text': remaining})}\n\n"

            full_reply = " ".join(accumulated_sentences).strip()
            if full_reply and not current_cancel.is_set():
                asyncio.create_task(speak_text(full_reply, request_start_time=t_start))

            if db is not None and full_reply and not current_cancel.is_set():
                try:
                    log_entry = models.AuditLog(
                        command_input=transcript,
                        execution_status="success",
                        telemetry_data=json.dumps({"response": full_reply})
                    )
                    db.add(log_entry)
                    db.commit()
                except Exception as db_err:
                    print(f"[Database Warning]: {db_err}")

            if os.getenv("DEBUG_TIMING", "0") == "1":
                total_ms = (time.perf_counter() - t_start) * 1000
                print(f"[TIMING] Total time: {total_ms:.1f}ms", flush=True)

            yield f"event: done\ndata: {json.dumps({'status': 'done'})}\n\n"

        return StreamingResponse(
            voice_stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    except sr.UnknownValueError:
        msg = "Could not decipher speech audio."
        asyncio.create_task(speak_text(msg))
        if not is_sse:
            return {"status": "unclear", "transcript": "", "reply": msg, "executed": None}
        async def unclear_gen():
            yield f"event: transcript\ndata: {json.dumps({'transcript': ''})}\n\n"
            yield f"event: token\ndata: {json.dumps({'text': msg})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'done'})}\n\n"
        return StreamingResponse(unclear_gen(), media_type="text/event-stream")

    except Exception as e:
        err_msg = str(e)
        if not is_sse:
            return {"status": "error", "transcript": "", "reply": err_msg, "executed": None}
        async def err_gen():
            yield f"event: transcript\ndata: {json.dumps({'transcript': ''})}\n\n"
            yield f"event: token\ndata: {json.dumps({'text': err_msg})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'done'})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

@app.post("/macros")
def create_macro(payload: MacroCreatePayload, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")
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
        print(f"[Database Error]: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@app.get("/macros")
def list_macros(db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")
    try:
        return db.query(models.VoiceMacro).all()
    except Exception as e:
        print(f"[Database Error]: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@app.get("/audit-logs")
def get_audit_logs(limit: int = 15, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")
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
    except Exception as e:
        print(f"[Database Error]: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@app.get("/chat-history")
def get_chat_history(db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")
    try:
        messages = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == 1).order_by(models.ChatMessage.timestamp.asc()).all()
        return [{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in messages]
    except Exception as e:
        print(f"[Database Error]: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@app.post("/chat-memory/clear")
def clear_chat_memory(
    current_user: models.User = Depends(get_current_user),
    db: Optional[Session] = Depends(get_db)
):
    """Deletes the current user's chat messages. Requires a valid token. Returns count of deleted messages."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")
    try:
        deleted_count = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == 1).delete()
        db.commit()
        return {"status": "success", "deleted_count": deleted_count}
    except Exception as e:
        db.rollback()
        print(f"[Database Error]: Clear chat memory failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to clear chat memory.")

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
async def visual_click(payload: VisualClickPayload, db: Optional[Session] = Depends(get_db)):
    try:
        result_msg = click_bounding_box(payload.box_index, payload.bounding_boxes)

        if db is not None:
            try:
                log_entry = models.AuditLog(
                    command_input=f"Visual Click Box #{payload.box_index}",
                    execution_status="success",
                    telemetry_data=json.dumps({"action": "visual_click", "result": result_msg})
                )
                db.add(log_entry)
                db.commit()
            except Exception as db_err:
                print(f"[Database Warning]: {db_err}")

        return {"status": "success", "reply": result_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
