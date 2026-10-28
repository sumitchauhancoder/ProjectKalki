import os
import subprocess
import asyncio
import edge_tts
import re
import uuid
from pathlib import Path
from typing import Optional, Callable

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

async def _play_file_native(output_path_str: str):
    """Plays an audio file via Windows PowerShell MediaPlayer."""
    ps_cmd = (
        f"Add-Type -AssemblyName presentationCore; "
        f"$player = New-Object System.Windows.Media.MediaPlayer; "
        f"$player.Open('{output_path_str}'); "
        f"$player.Play(); "
        f"Start-Sleep -s 1; "
        f"while ($player.NaturalDuration.HasTimeSpan -and $player.Position -lt $player.NaturalDuration.TimeSpan) {{ Start-Sleep -m 100 }}"
    )
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            ["powershell", "-c", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    )

async def _tts_worker():
    """Sequential worker task that processes speech jobs from the queue one at a time."""
    global playback_hook
    while True:
        try:
            text = await _speech_queue.get()
            output_file = None
            try:
                # If a test or mock playback hook is registered, use it
                if playback_hook is not None:
                    res = playback_hook(text)
                    if asyncio.iscoroutine(res):
                        await res
                else:
                    voice = detect_language(text)
                    output_file = get_unique_tts_path()
                    output_path_str = str(output_file).replace("\\", "/")

                    # Generate speech with 15-second timeout
                    try:
                        communicate = edge_tts.Communicate(text, voice)
                        await asyncio.wait_for(communicate.save(output_path_str), timeout=15.0)
                    except asyncio.TimeoutError:
                        print("[TTS Warning]: Edge-TTS speech generation timed out.")
                        continue
                    except Exception as gen_err:
                        print(f"[TTS Error]: Edge-TTS generation failed: {type(gen_err).__name__}")
                        continue

                    # Play sequentially (one item at a time)
                    if output_file.exists():
                        await _play_file_native(output_path_str)

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
    global _speech_queue, _worker_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if _speech_queue is None:
        _speech_queue = asyncio.Queue()
        _worker_task = None
    elif loop is not None and getattr(_speech_queue, "_loop", None) not in (loop, None):
        _speech_queue = asyncio.Queue()
        _worker_task = None

    if loop is not None and (_worker_task is None or _worker_task.done()):
        _worker_task = loop.create_task(_tts_worker())

    return _speech_queue

async def enqueue_speech(text: str):
    """Enqueues a speech job into the single TTS queue."""
    if not text or len(text.strip()) == 0:
        return
    q = get_tts_queue()
    await q.put(text.strip())

async def speak_text(text: str):
    """
    Public entrypoint for TTS requests.
    Enqueues the text into the single background worker queue without blocking caller.
    """
    await enqueue_speech(text)
