import os
import subprocess
import asyncio
import edge_tts
import re
import uuid
import time
from pathlib import Path
from typing import Optional, Callable, Union

VOICE_MAP = {
    "kannada": "kn-IN-GaganNeural",
    "hindi": "hi-IN-MadhurNeural",
    "english_in": "en-IN-PrabhatNeural",
    "english_us": "en-US-ChristopherNeural"
}

TTS_CACHE_DIR = Path(__file__).resolve().parent / "tts_cache"

def detect_language(text: str) -> str:
    """Detects Kannada, Hindi, or English text ranges."""
    if re.search(r'[\u0C80-\u0CFF]', text):
        return VOICE_MAP["kannada"]
    elif re.search(r'[\u0900-\u097F]', text):
        return VOICE_MAP["hindi"]
    else:
        return VOICE_MAP["english_in"]

def get_unique_tts_path() -> Path:
    """Generates a unique uuid4-based mp3 filepath inside backend/tts_cache/."""
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return TTS_CACHE_DIR / f"{uuid.uuid4().hex}.mp3"

# Playback hook for testing or custom handlers
playback_hook: Optional[Callable] = None

# Internal queue and worker task references
_speech_queue: Optional[asyncio.Queue] = None
_worker_task: Optional[asyncio.Task] = None
_worker_loop: Optional[asyncio.AbstractEventLoop] = None

_audio_player_initialized = False
_cancel_flag = False

def init_audio_player():
    """Initializes persistent pygame.mixer audio player."""
    global _audio_player_initialized
    if not _audio_player_initialized:
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            _audio_player_initialized = True
        except Exception as e:
            print(f"[TTS Audio Warning]: pygame.mixer init failed: {e}")

def cancel_playback_and_queue():
    """Immediately stops active audio playback and purges all queued speech items."""
    global _cancel_flag, _speech_queue
    _cancel_flag = True
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass

    if _speech_queue is not None:
        while not _speech_queue.empty():
            try:
                _speech_queue.get_nowait()
                _speech_queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break

def reset_cancel():
    """Resets the cancellation flag for new speech requests."""
    global _cancel_flag
    _cancel_flag = False

def is_cancelled() -> bool:
    """Returns True if current playback and generation are cancelled."""
    return _cancel_flag

async def _play_file_persistent(output_path_str: str):
    """Plays an audio file via persistent pygame.mixer with responsive interruption."""
    init_audio_player()
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(output_path_str)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if _cancel_flag:
                pygame.mixer.music.stop()
                break
            await asyncio.sleep(0.03)
    except Exception as e:
        print(f"[Audio Error]: pygame playback failed: {type(e).__name__}")
    finally:
        try:
            import pygame
            pygame.mixer.music.unload()
        except Exception:
            pass

async def _tts_worker():
    """Sequential worker task that processes speech jobs from the queue one at a time."""
    global playback_hook
    while True:
        try:
            job = await _speech_queue.get()
            if _cancel_flag:
                _speech_queue.task_done()
                continue

            if isinstance(job, dict):
                text = job["text"]
                req_start = job.get("request_start_time")
            elif isinstance(job, tuple) and len(job) == 2:
                text, req_start = job
            else:
                text = str(job)
                req_start = None

            output_file = None
            try:
                # If a test or mock playback hook is registered, use it
                if playback_hook is not None:
                    res = playback_hook(text)
                    if asyncio.iscoroutine(res):
                        await res
                else:
                    if _cancel_flag:
                        continue

                    voice = detect_language(text)
                    output_file = get_unique_tts_path()
                    output_path_str = str(output_file).replace("\\", "/")

                    # Generate speech with 15-second timeout
                    t_gen_start = time.perf_counter()
                    try:
                        communicate = edge_tts.Communicate(text, voice)
                        await asyncio.wait_for(communicate.save(output_path_str), timeout=15.0)
                    except asyncio.TimeoutError:
                        print("[TTS Warning]: Edge-TTS speech generation timed out.")
                        continue
                    except Exception as gen_err:
                        print(f"[TTS Error]: Edge-TTS generation failed: {type(gen_err).__name__}")
                        continue
                    t_gen_end = time.perf_counter()

                    if _cancel_flag:
                        continue

                    if req_start is not None and os.getenv("DEBUG_TIMING", "0") == "1":
                        gen_ms = (t_gen_end - t_gen_start) * 1000
                        playback_start_ms = (time.perf_counter() - req_start) * 1000
                        print(f"[TIMING] TTS generation time: {gen_ms:.1f}ms", flush=True)
                        print(f"[TIMING] Time until audio playback starts: {playback_start_ms:.1f}ms", flush=True)

                    # Play sequentially via persistent player
                    if output_file.exists() and not _cancel_flag:
                        await _play_file_persistent(output_path_str)

            except Exception as item_err:
                print(f"[TTS Error]: {type(item_err).__name__}")
            finally:
                # Always delete the mp3 file after playback finishes, inside try/except
                if output_file is not None:
                    try:
                        if output_file.exists():
                            output_file.unlink()
                    except Exception:
                        pass
                _speech_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as loop_err:
            print(f"[TTS Worker Error]: {type(loop_err).__name__}")

def get_tts_queue() -> asyncio.Queue:
    """Returns the single asyncio.Queue, initializing the worker if needed."""
    global _speech_queue, _worker_task, _worker_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if _speech_queue is None or (loop is not None and _worker_loop is not loop):
        _speech_queue = asyncio.Queue()
        _worker_task = None
        _worker_loop = loop

    if loop is not None and (_worker_task is None or _worker_task.done()):
        _worker_task = loop.create_task(_tts_worker())
        _worker_loop = loop

    return _speech_queue

async def enqueue_speech(text: str, request_start_time: Optional[float] = None):
    """Enqueues a speech job into the single TTS queue."""
    if not text or len(text.strip()) == 0:
        return
    q = get_tts_queue()
    await q.put({"text": text.strip(), "request_start_time": request_start_time})

async def speak_text(text: str, request_start_time: Optional[float] = None):
    """
    Public entrypoint for TTS requests.
    Enqueues the text into the single background worker queue without blocking caller.
    """
    await enqueue_speech(text, request_start_time=request_start_time)
