import os
import subprocess
import asyncio
import edge_tts
import re
import uuid
import time
import shutil
from pathlib import Path
from typing import Optional, Callable, Union

VOICE_MAP = {
    "kannada": "kn-IN-GaganNeural",
    "hindi": "hi-IN-MadhurNeural",
    "english_in": "en-IN-PrabhatNeural",
    "english_us": "en-US-ChristopherNeural"
}

TTS_CACHE_DIR = Path(__file__).resolve().parent / "tts_cache"
_debug_counter = 0

def get_debug_audio_dir() -> Path:
    """Returns directory for saving debug MP3 files."""
    app_data = os.getenv("APPDATA")
    if app_data:
        debug_dir = Path(app_data) / "KALKI" / "debug_audio"
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            return debug_dir
        except Exception:
            pass
    fallback = Path(__file__).resolve().parent / "debug_audio"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

def clean_for_speech(text: str) -> str:
    """
    Cleans raw markdown and symbols from text before passing to TTS.
    - Strips markdown links, code blocks, backticks, bold/italics, headers, table pipes.
    - Expands '%' to ' percent '.
    - Strips arrows (→, ->) and emojis.
    - Strips leading list numbers ('1. ', '2. ') and bullet markers.
    - Collapses repeated punctuation ('!!', '??', '...').
    - Preserves Indic characters (Devanagari, Kannada), numbers, and natural sentence punctuation.
    """
    if not text:
        return ""
    # 1. Expand %
    s = re.sub(r'(\d+)\s*%', r'\1 percent', text)
    s = s.replace('%', ' percent ')
    # 2. Markdown links: [text](url) -> text
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
    # 3. Inline code and code blocks: backticks
    s = re.sub(r'`+([^`]+)`+', r'\1', s)
    s = s.replace('`', '')
    # 4. Bold and italics: **text**, *text*, __text__, _text_
    s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
    s = re.sub(r'\*([^*]+)\*', r'\1', s)
    s = re.sub(r'__([^_]+)__', r'\1', s)
    s = re.sub(r'_([^_]+)_', r'\1', s)
    s = s.replace('*', '')
    # 5. Arrows
    s = re.sub(r'(->|<-|-->|<--|=>|<=|→|←)', ' ', s)
    # 6. Table pipes
    s = s.replace('|', ' ')
    # 7. Emojis and miscellaneous symbols (supplementary planes & dingbats)
    s = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]', '', s)
    # 8. Leading bullet markers, headers, and list numbers
    lines = s.split('\n')
    cleaned_lines = []
    for line in lines:
        l = line.strip()
        l = re.sub(r'^#{1,6}\s*', '', l)
        l = re.sub(r'^[-*+]\s+', '', l)
        l = re.sub(r'^\d+[\.\)]\s+', '', l)
        if l:
            cleaned_lines.append(l)
    s = ' '.join(cleaned_lines)
    # 9. Repeated punctuation: '!!' -> '!', '??' -> '?', '...' -> '.'
    s = re.sub(r'!+', '!', s)
    s = re.sub(r'\?+', '?', s)
    s = re.sub(r'\.{2,}', '.', s)
    # 10. Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def get_dominant_script(text: str) -> str:
    """
    Identifies the dominant script using character counts:
    - Kannada (U+0C80 to U+0CFF) -> 'kannada'
    - Devanagari (U+0900 to U+097F) -> 'hindi'
    - Latin letters -> 'english'
    - Anything else (Chinese, Japanese, symbols, no letters) -> 'english'
    """
    kn_count = len(re.findall(r'[\u0C80-\u0CFF]', text))
    hi_count = len(re.findall(r'[\u0900-\u097F]', text))
    en_count = len(re.findall(r'[a-zA-Z]', text))

    if kn_count > hi_count and kn_count > en_count:
        return "kannada"
    elif hi_count > kn_count and hi_count > en_count:
        return "hindi"
    else:
        return "english"

def detect_language(text: str) -> str:
    """
    Picks default voice from dominant script:
    Kannada -> kn-IN-GaganNeural, Hindi -> hi-IN-MadhurNeural, English / others -> en-IN-PrabhatNeural.
    A Kannada or Hindi voice is never used for another script.
    """
    script = get_dominant_script(text)
    if script == "kannada":
        return VOICE_MAP["kannada"]
    elif script == "hindi":
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
_ready_playback_queue: Optional[asyncio.Queue] = None
_synthesis_task: Optional[asyncio.Task] = None
_playback_task: Optional[asyncio.Task] = None
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
    """Immediately stops active audio playback and purges all queued and prefetched speech items."""
    global _cancel_flag, _speech_queue, _ready_playback_queue
    _cancel_flag = True
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.stop()
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass

    # 1. Drain ready playback queue and delete any unplayed prefetched audio files
    if _ready_playback_queue is not None:
        while not _ready_playback_queue.empty():
            try:
                item = _ready_playback_queue.get_nowait()
                if isinstance(item, dict):
                    f = item.get("file")
                    if f is not None:
                        try:
                            if isinstance(f, Path) and f.exists():
                                f.unlink()
                            elif isinstance(f, str) and os.path.exists(f):
                                os.unlink(f)
                        except Exception:
                            pass
                _ready_playback_queue.task_done()
                if _speech_queue is not None:
                    try:
                        _speech_queue.task_done()
                    except ValueError:
                        pass
            except (asyncio.QueueEmpty, ValueError):
                break

    # 2. Drain pending text speech queue
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
    """Plays an audio file via persistent pygame.mixer with responsive interruption and bounded tail."""
    init_audio_player()
    channel = None
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        sound = pygame.mixer.Sound(output_path_str)
        sound_len = sound.get_length()
        channel = pygame.mixer.find_channel(True) or pygame.mixer.Channel(0)
        channel.play(sound)

        t0 = time.perf_counter()
        while channel.get_busy() and (time.perf_counter() - t0) < (sound_len + 0.05):
            if _cancel_flag:
                channel.stop()
                break
            await asyncio.sleep(0.01)
        channel.stop()
    except Exception as e:
        print(f"[Audio Error]: pygame playback failed: {type(e).__name__}")
    finally:
        try:
            if channel is not None and channel.get_busy():
                channel.stop()
        except Exception:
            pass

async def _synthesis_worker():
    """Worker task that synthesizes speech for incoming text jobs into a bounded ready queue."""
    global playback_hook, _debug_counter
    while True:
        try:
            job = await _speech_queue.get()
            if _cancel_flag:
                _speech_queue.task_done()
                continue

            if isinstance(job, dict):
                text = job.get("text", "")
                req_start = job.get("request_start_time")
            elif isinstance(job, tuple) and len(job) == 2:
                text, req_start = job
            else:
                text = str(job)
                req_start = None

            cleaned_text = clean_for_speech(text)
            if not cleaned_text:
                _speech_queue.task_done()
                continue

            voice = detect_language(cleaned_text)

            if os.getenv("DEBUG_AUDIO", "0") == "1":
                dominant_script = get_dominant_script(cleaned_text)
                print(f"[DEBUG_AUDIO] Voice: {voice} | Script: {dominant_script}", flush=True)

            # If a test or mock playback hook is registered, skip actual edge-tts synthesis
            if playback_hook is not None:
                await _ready_playback_queue.put({
                    "mock": True,
                    "text": cleaned_text,
                    "file": None,
                    "path_str": None,
                    "req_start": req_start
                })
                continue

            if _cancel_flag:
                _speech_queue.task_done()
                continue

            output_file = get_unique_tts_path()
            output_path_str = str(output_file).replace("\\", "/")

            t_gen_start = time.perf_counter()
            try:
                communicate = edge_tts.Communicate(cleaned_text, voice, rate="+0%")
                await asyncio.wait_for(communicate.save(output_path_str), timeout=15.0)
            except asyncio.TimeoutError:
                print("[TTS Warning]: Edge-TTS speech generation timed out.", flush=True)
                _speech_queue.task_done()
                continue
            except Exception as gen_err:
                print(f"[TTS Error]: Edge-TTS generation failed: {type(gen_err).__name__}", flush=True)
                _speech_queue.task_done()
                continue
            t_gen_end = time.perf_counter()

            if _cancel_flag:
                try:
                    if output_file.exists():
                        output_file.unlink()
                except Exception:
                    pass
                _speech_queue.task_done()
                continue

            # In DEBUG_AUDIO mode, save a numbered copy to debug_audio dir
            if os.getenv("DEBUG_AUDIO", "0") == "1" and output_file.exists():
                try:
                    debug_dir = get_debug_audio_dir()
                    _debug_counter += 1
                    debug_file = debug_dir / f"audio_{_debug_counter:03d}.mp3"
                    shutil.copyfile(output_file, debug_file)
                except Exception:
                    pass

            if req_start is not None and os.getenv("DEBUG_TIMING", "0") == "1":
                gen_ms = (t_gen_end - t_gen_start) * 1000
                print(f"[TIMING] TTS generation time: {gen_ms:.1f}ms", flush=True)

            # Put into ready playback queue. Maxsize=2 caps prefetching at 2 sentences ahead.
            await _ready_playback_queue.put({
                "mock": False,
                "text": cleaned_text,
                "file": output_file,
                "path_str": output_path_str,
                "req_start": req_start,
                "gen_ms": (t_gen_end - t_gen_start) * 1000
            })

            # Check again if cancelled while waiting to put into queue
            if _cancel_flag and output_file.exists():
                try:
                    output_file.unlink()
                except Exception:
                    pass

        except asyncio.CancelledError:
            break
        except Exception as loop_err:
            print(f"[TTS Synthesis Error]: {type(loop_err).__name__}", flush=True)

async def _playback_worker():
    """Worker task that sequentially plays synthesized audio files from the ready queue."""
    global playback_hook
    while True:
        try:
            item = await _ready_playback_queue.get()
            output_file = item.get("file")
            try:
                if _cancel_flag:
                    continue

                if item.get("mock") or playback_hook is not None:
                    res = playback_hook(item["text"])
                    if asyncio.iscoroutine(res):
                        await res
                else:
                    path_str = item.get("path_str")
                    req_start = item.get("req_start")
                    if req_start is not None and os.getenv("DEBUG_TIMING", "0") == "1":
                        playback_start_ms = (time.perf_counter() - req_start) * 1000
                        print(f"[TIMING] Time until audio playback starts: {playback_start_ms:.1f}ms", flush=True)

                    if output_file is not None and output_file.exists() and not _cancel_flag:
                        await _play_file_persistent(path_str)

            except Exception as play_err:
                print(f"[TTS Playback Error]: {type(play_err).__name__}", flush=True)
            finally:
                if output_file is not None:
                    try:
                        if output_file.exists():
                            output_file.unlink()
                    except Exception:
                        pass
                _ready_playback_queue.task_done()
                _speech_queue.task_done()

        except asyncio.CancelledError:
            break
        except Exception as loop_err:
            print(f"[TTS Playback Loop Error]: {type(loop_err).__name__}", flush=True)

def get_tts_queue() -> asyncio.Queue:
    """Returns the single asyncio.Queue, initializing the synthesis and playback workers if needed."""
    global _speech_queue, _ready_playback_queue, _synthesis_task, _playback_task, _worker_task, _worker_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if _speech_queue is None or (loop is not None and _worker_loop is not loop):
        _speech_queue = asyncio.Queue()
        _ready_playback_queue = asyncio.Queue(maxsize=2)
        _synthesis_task = None
        _playback_task = None
        _worker_task = None
        _worker_loop = loop

    if loop is not None:
        if _synthesis_task is None or _synthesis_task.done():
            _synthesis_task = loop.create_task(_synthesis_worker())
        if _playback_task is None or _playback_task.done():
            _playback_task = loop.create_task(_playback_worker())
        _worker_task = _playback_task
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
