import os
import re
import subprocess
import asyncio
import threading
import queue
import time
import shutil
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import pyautogui
from google import genai
from google.genai import types
from groq import Groq

# Load .env explicitly from the backend/ folder relative to this file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Model names change over time; verify against official documentation:
# - Google Gemini: https://ai.google.dev/gemini-api/docs/models
# - Groq: https://console.groq.com/docs/models
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"  # Verify in https://ai.google.dev/gemini-api/docs/models
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"  # Verify in https://console.groq.com/docs/models

# --------------------------------------------------------------------------
# Group 1: Local System and App Control Configuration (APP_COMMANDS)
# --------------------------------------------------------------------------
APP_COMMANDS = {
    # Text & Code Editors
    "notepad": "notepad.exe",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "code": "code",

    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",
    "edge": "msedge.exe",

    # Calculators & System Utilities
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "my computer": "explorer.exe",
    "this pc": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "windows settings": "ms-settings:",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",

    # Productivity / Office Suite
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",

    # Media & Communication
    "spotify": "spotify.exe",
    "vlc": "vlc.exe",
    "zoom": "zoom.exe",
    "teams": "teams.exe",
    "discord": "discord.exe",
}

APP_MAP = APP_COMMANDS

_pending_action: Optional[str] = None
_pending_action_timestamp: float = 0.0

def get_gemini_client():
    """Initializes Google GenAI client if GEMINI_API_KEY is available."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key.strip():
        try:
            return genai.Client(
                api_key=api_key.strip(),
                http_options=types.HttpOptions(timeout=10000)
            )
        except Exception as e:
            print(f"[LLM Engine] Could not initialize Gemini client: {type(e).__name__}")
    return None

def get_groq_client():
    """Initializes Groq client if GROQ_API_KEY is available."""
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.strip():
        try:
            return Groq(api_key=api_key.strip(), timeout=10.0)
        except Exception as e:
            print(f"[LLM Engine] Could not initialize Groq client: {type(e).__name__}")
    return None

# Module-level client instances
client = get_gemini_client()
groq_client = get_groq_client()

def find_app_executable(exe_name: str) -> Optional[str]:
    """Finds path to executable on PATH, Windows Registry, or common install locations."""
    if not exe_name or exe_name.startswith("ms-settings:"):
        return exe_name

    found = shutil.which(exe_name)
    if found:
        return found

    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                sub_key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
                with winreg.OpenKey(root, sub_key) as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    if val and Path(val).exists():
                        return val
            except Exception:
                pass
    except Exception:
        pass

    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")

    candidates = [
        Path(prog_files) / exe_name,
        Path(prog_files_x86) / exe_name,
    ]
    if local_app_data:
        candidates.extend([
            Path(local_app_data) / "Programs" / exe_name,
            Path(local_app_data) / "Microsoft" / "WindowsApps" / exe_name,
        ])
    if app_data:
        candidates.append(Path(app_data) / exe_name)

    for c in candidates:
        if c.exists():
            return str(c)

    return None

def launch_application(app_name: str) -> str:
    clean_name = app_name.lower().strip()
    if clean_name not in APP_COMMANDS:
        return f"I couldn't find {app_name} installed on this computer."

    exe_target = APP_COMMANDS[clean_name]

    if exe_target == "ms-settings:":
        try:
            subprocess.Popen(["explorer.exe", "ms-settings:"])
            return "Opening settings."
        except Exception:
            return "I couldn't find settings installed on this computer."

    resolved = find_app_executable(exe_target)
    target = resolved or exe_target

    try:
        if resolved is None and clean_name in ["word", "excel", "powerpoint", "outlook", "spotify", "vlc", "zoom", "teams", "discord"]:
            if not shutil.which(exe_target):
                raise FileNotFoundError(f"{exe_target} not found")

        subprocess.Popen([target])
        if clean_name in ["calculator", "calc"]:
            return f"Launched {clean_name}"
        return f"Opening {app_name}."
    except FileNotFoundError:
        return f"I couldn't find {app_name} installed on this computer."
    except Exception as e:
        return f"Failed to launch {app_name}: {str(e)}"

def close_application(app_name: str) -> str:
    clean_name = app_name.lower().strip()
    if clean_name not in APP_COMMANDS:
        return f"I couldn't find {app_name} running."

    exe_target = APP_COMMANDS[clean_name]
    if exe_target == "ms-settings:":
        exe_target = "SystemSettings.exe"
    elif exe_target == "code":
        exe_target = "Code.exe"

    if not exe_target.lower().endswith(".exe"):
        exe_name = f"{exe_target}.exe"
    else:
        exe_name = exe_target

    try:
        proc = subprocess.run(["taskkill", "/IM", exe_name, "/F"], capture_output=True, text=True)
        if proc.returncode == 0:
            return f"Closed {app_name}."
        else:
            return f"I couldn't find {app_name} running."
    except Exception:
        return f"I couldn't find {app_name} running."

def get_volume_interface():
    """Returns the pycaw audio endpoint volume controller."""
    from pycaw.pycaw import AudioUtilities
    speakers = AudioUtilities.GetSpeakers()
    if hasattr(speakers, "EndpointVolume"):
        return speakers.EndpointVolume
    elif hasattr(speakers, "Activate"):
        from pycaw.pycaw import IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    return speakers

def handle_volume_control(prompt: str) -> Optional[str]:
    """Processes volume adjustment and mute commands."""
    if prompt in ["mute", "mute volume", "silence"]:
        try:
            vol = get_volume_interface()
            vol.SetMute(1, None)
            return "Volume muted."
        except Exception as e:
            return f"Failed to mute volume: {e}"

    if prompt in ["unmute", "unmute volume"]:
        try:
            vol = get_volume_interface()
            vol.SetMute(0, None)
            return "Volume unmuted."
        except Exception as e:
            return f"Failed to unmute volume: {e}"

    set_match = re.search(r'\b(?:set\s+volume\s+(?:to\s+)?|volume\s+to\s+|volume\s+)(\d{1,3})\b', prompt)
    if not set_match:
        set_match = re.search(r'\b(\d{1,3})\s*(?:percent\s+volume|%\s*volume)\b', prompt)

    if set_match:
        val = int(set_match.group(1))
        val = max(0, min(100, val))
        try:
            vol = get_volume_interface()
            vol.SetMasterVolumeLevelScalar(val / 100.0, None)
            return f"Volume set to {val} percent."
        except Exception as e:
            return f"Failed to set volume: {e}"

    if prompt in ["volume up", "increase volume", "louder", "turn volume up", "turn it up"]:
        try:
            vol = get_volume_interface()
            cur = vol.GetMasterVolumeLevelScalar()
            new_val = min(1.0, cur + 0.10)
            vol.SetMasterVolumeLevelScalar(new_val, None)
            return "Volume increased."
        except Exception as e:
            return f"Failed to increase volume: {e}"

    if prompt in ["volume down", "decrease volume", "quieter", "lower volume", "turn volume down", "turn it down"]:
        try:
            vol = get_volume_interface()
            cur = vol.GetMasterVolumeLevelScalar()
            new_val = max(0.0, cur - 0.10)
            vol.SetMasterVolumeLevelScalar(new_val, None)
            return "Volume decreased."
        except Exception as e:
            return f"Failed to decrease volume: {e}"

    return None

def handle_brightness_control(prompt: str) -> Optional[str]:
    """Processes monitor screen brightness commands."""
    set_br_match = re.search(r'\b(?:set\s+brightness\s+(?:to\s+)?|brightness\s+to\s+|brightness\s+)(\d{1,3})\b', prompt)
    if not set_br_match:
        set_br_match = re.search(r'\b(\d{1,3})\s*(?:percent\s+brightness|%\s*brightness)\b', prompt)

    if set_br_match:
        val = int(set_br_match.group(1))
        val = max(0, min(100, val))
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(val)
            return f"Brightness set to {val} percent."
        except Exception:
            return "Brightness control is not supported on this machine."

    if prompt in ["brightness up", "increase brightness", "more brightness", "turn brightness up"]:
        try:
            import screen_brightness_control as sbc
            cur_list = sbc.get_brightness()
            cur = cur_list[0] if (isinstance(cur_list, list) and cur_list) else 50
            new_val = min(100, cur + 10)
            sbc.set_brightness(new_val)
            return "Brightness increased."
        except Exception:
            return "Brightness control is not supported on this machine."

    if prompt in ["brightness down", "decrease brightness", "lower brightness", "less brightness", "turn brightness down"]:
        try:
            import screen_brightness_control as sbc
            cur_list = sbc.get_brightness()
            cur = cur_list[0] if (isinstance(cur_list, list) and cur_list) else 50
            new_val = max(0, cur - 10)
            sbc.set_brightness(new_val)
            return "Brightness decreased."
        except Exception:
            return "Brightness control is not supported on this machine."

    return None

def take_screenshot() -> str:
    """Takes a full screen screenshot and saves it to %USERPROFILE%/Pictures/KALKI Screenshots/."""
    from datetime import datetime
    user_profile = os.environ.get("USERPROFILE", str(Path.home()))
    folder = Path(user_profile) / "Pictures" / "KALKI Screenshots"
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"kalki_{timestamp}.png"
    filepath = folder / filename

    saved = False
    try:
        import mss
        with mss.mss() as sct:
            sct.shot(output=str(filepath))
            saved = filepath.exists()
    except Exception:
        saved = False

    if not saved:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(str(filepath))
            saved = True
        except Exception:
            try:
                import pyautogui
                img = pyautogui.screenshot()
                img.save(str(filepath))
                saved = True
            except Exception as e:
                return f"Failed to take screenshot: {e}"

    return f"Screenshot saved to Pictures/KALKI Screenshots/{filename}"

def fast_path_local_router(user_prompt: str):
    """0ms Instant local execution for Group 1 app and system control commands."""
    global _pending_action, _pending_action_timestamp
    prompt = user_prompt.lower().strip()
    now = time.time()

    # Expire pending action after 30 seconds
    if _pending_action is not None and (now - _pending_action_timestamp > 30.0):
        _pending_action = None

    # Handle confirmation or cancellation if an action is pending
    if _pending_action is not None:
        action = _pending_action
        if prompt in ["yes", "confirm", "okay", "ok", "yep", "yeah", "yes please", "sure"]:
            _pending_action = None
            if action == "shutdown":
                subprocess.Popen(["shutdown", "/s", "/t", "5"])
                return True, {"reply": "Shutting down in 5 seconds.", "tool_executed": "Fast-Path Local: shutdown"}
            elif action == "restart":
                subprocess.Popen(["shutdown", "/r", "/t", "5"])
                return True, {"reply": "Restarting in 5 seconds.", "tool_executed": "Fast-Path Local: restart"}
        elif prompt in ["no", "cancel", "stop", "abort", "nope", "never mind", "dont", "don't"]:
            _pending_action = None
            return True, {"reply": "Cancelled.", "tool_executed": "Fast-Path Local: cancel_pending_action"}

    # Identity queries
    if prompt in ["who are you", "who are you?", "what is your name", "what is your name?"]:
        return True, {
            "reply": "I am KALKI, your autonomous multi-lingual desktop AI core assistant.",
            "tool_executed": "Local Identity Engine"
        }

    # Volume control commands
    vol_res = handle_volume_control(prompt)
    if vol_res:
        return True, {"reply": vol_res, "tool_executed": f"Fast-Path Local: {vol_res}"}

    # Brightness control commands
    bright_res = handle_brightness_control(prompt)
    if bright_res:
        return True, {"reply": bright_res, "tool_executed": f"Fast-Path Local: {bright_res}"}

    # Shutdown initiation
    if prompt in ["shutdown", "shut down", "turn off computer", "turn off pc", "power off"]:
        _pending_action = "shutdown"
        _pending_action_timestamp = time.time()
        return True, {
            "reply": "Are you sure you want to shut down? Say yes to confirm.",
            "tool_executed": "Fast-Path Local: shutdown_confirmation_request"
        }

    # Restart initiation
    if prompt in ["restart", "reboot", "restart computer", "restart pc"]:
        _pending_action = "restart"
        _pending_action_timestamp = time.time()
        return True, {
            "reply": "Are you sure you want to restart? Say yes to confirm.",
            "tool_executed": "Fast-Path Local: restart_confirmation_request"
        }

    # Abort/cancel shutdown
    if prompt in ["cancel shutdown", "abort shutdown"]:
        _pending_action = None
        try:
            subprocess.Popen(["shutdown", "/a"])
        except Exception:
            pass
        return True, {
            "reply": "Shutdown cancelled.",
            "tool_executed": "Fast-Path Local: abort_shutdown"
        }

    # Lock screen
    if prompt in ["lock screen", "lock computer", "lock pc"]:
        try:
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            return True, {"reply": "Locking screen.", "tool_executed": "Fast-Path Local: lock_workstation"}
        except Exception as e:
            return True, {"reply": f"Failed to lock screen: {e}", "tool_executed": "Fast-Path Local: lock_workstation"}

    # Sleep
    if prompt in ["sleep", "sleep mode", "put computer to sleep"]:
        try:
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return True, {"reply": "Putting computer to sleep.", "tool_executed": "Fast-Path Local: sleep"}
        except Exception as e:
            return True, {"reply": f"Failed to put computer to sleep: {e}", "tool_executed": "Fast-Path Local: sleep"}

    # Screenshot
    if prompt in ["take a screenshot", "screenshot", "capture screen", "take screenshot"]:
        res = take_screenshot()
        return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}

    # App Open / Launch
    open_match = re.search(r'^(?:please\s+)?(?:open|launch|start|run)\s+(?:up\s+)?(?:the\s+)?([a-z0-9\s\.\-_]+)$', prompt)
    if open_match:
        target_raw = open_match.group(1).strip()
        matched_app = None
        for app_name in sorted(APP_COMMANDS.keys(), key=len, reverse=True):
            if target_raw == app_name or target_raw == f"the {app_name}":
                matched_app = app_name
                break
        if not matched_app:
            for app_name in sorted(APP_COMMANDS.keys(), key=len, reverse=True):
                if app_name in target_raw.split():
                    matched_app = app_name
                    break

        if matched_app:
            res = launch_application(matched_app)
            return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}

    # App Close / Exit
    close_match = re.search(r'^(?:please\s+)?(?:close|exit|quit|kill|terminate)\s+(?:the\s+)?([a-z0-9\s\.\-_]+)$', prompt)
    if close_match:
        target_raw = close_match.group(1).strip()
        matched_app = None
        for app_name in sorted(APP_COMMANDS.keys(), key=len, reverse=True):
            if target_raw == app_name or target_raw == f"the {app_name}":
                matched_app = app_name
                break
        if not matched_app:
            for app_name in sorted(APP_COMMANDS.keys(), key=len, reverse=True):
                if app_name in target_raw.split():
                    matched_app = app_name
                    break

        if matched_app:
            res = close_application(matched_app)
            return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}

    # Type text
    if prompt.startswith("type ") or prompt.startswith("write "):
        text_to_type = prompt.split(" ", 1)[1]
        pyautogui.write(text_to_type, interval=0.01)
        return True, {"reply": f"Typed: '{text_to_type}'", "tool_executed": "Fast-Path Local: type_text"}

    return False, None

JARVIS_SYSTEM_INSTRUCTION = """
You are KALKI, an autonomous multi-lingual J.A.R.V.I.S.-style AI core assistant.
Available local commands: open/close apps, volume control, brightness, lock screen, sleep, shutdown (with confirmation), restart (with confirmation), take screenshot.
Rules:
1. Reply in English unless the user explicitly asks for another language (for example 'reply in Kannada') or the language setting is set to another language.
2. Keep responses brief, sharp, concise, and authoritative.
3. Provide direct answers to general knowledge questions.
"""

def detect_reply_language(user_prompt: str) -> str:
    """
    Determines the reply language from the user prompt text.
    Honors explicit instructions (e.g. 'reply in Kannada', 'Kannada mein bolo', 'in Hindi').
    Detects scripts: Devanagari -> Hindi, Kannada -> Kannada.
    Defaults to English.
    """
    prompt_lower = user_prompt.lower()
    # Check for explicit language requests (explicit request wins)
    if (re.search(r'\b(?:reply|speak|answer|talk|respond)\s+in\s+kannada\b', prompt_lower)
            or re.search(r'\bkannada\s+(?:mein|me|alli)\s+(?:bolo|heli|mathadi)\b', prompt_lower)
            or re.search(r'\bin\s+kannada\b', prompt_lower)):
        return "kannada"
    if (re.search(r'\b(?:reply|speak|answer|talk|respond)\s+in\s+hindi\b', prompt_lower)
            or re.search(r'\bhindi\s+(?:mein|me)\s+bolo\b', prompt_lower)
            or re.search(r'\bin\s+hindi\b', prompt_lower)):
        return "hindi"
    if (re.search(r'\b(?:reply|speak|answer|talk|respond)\s+in\s+english\b', prompt_lower)
            or re.search(r'\benglish\s+(?:mein|me)\s+bolo\b', prompt_lower)
            or re.search(r'\bin\s+english\b', prompt_lower)):
        return "english"

    # Script-based detection
    kn_count = len(re.findall(r'[\u0C80-\u0CFF]', user_prompt))
    hi_count = len(re.findall(r'[\u0900-\u097F]', user_prompt))
    latin_count = len(re.findall(r'[a-zA-Z]', user_prompt))

    if kn_count > hi_count and kn_count > latin_count:
        return "kannada"
    if hi_count > kn_count and hi_count > latin_count:
        return "hindi"

    return "english"

def is_valid_script_reply(text: str, expected_lang: str) -> bool:
    """
    Verifies that most letters in text are in the expected script.
    - 'kannada': Kannada letters exceed other letters
    - 'hindi': Devanagari letters exceed other letters
    - 'english': Latin letters dominate (no CJK or Indic domination)
    """
    if not text or not text.strip():
        return True

    kn_count = len(re.findall(r'[\u0C80-\u0CFF]', text))
    hi_count = len(re.findall(r'[\u0900-\u097F]', text))
    latin_count = len(re.findall(r'[a-zA-Z]', text))
    cjk_count = len(re.findall(r'[\u4E00-\u9FFF\u3040-\u30FF]', text))

    total = kn_count + hi_count + latin_count + cjk_count
    if total == 0:
        return True

    if expected_lang == "kannada":
        return kn_count > (total - kn_count)
    elif expected_lang == "hindi":
        return hi_count > (total - hi_count)
    else:  # english
        return (kn_count + hi_count + cjk_count) <= latin_count

def get_language_instruction(lang: str) -> str:
    """Returns the explicit language instruction to override default English."""
    if lang == "hindi":
        return "Reply only in Hindi (Devanagari script)."
    elif lang == "kannada":
        return "Reply only in Kannada (Kannada script)."
    return "Reply in English."

VOICE_REPLY_INSTRUCTION = "For voice replies, answer in at most 2 short sentences unless the user asks for detail."

def build_system_instruction(user_prompt: str, is_voice: bool = False) -> str:
    """Builds dynamic system prompt embedding detected reply language instruction."""
    lang = detect_reply_language(user_prompt)
    lang_instruction = get_language_instruction(lang)
    instruction = f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\n{lang_instruction}"
    if is_voice:
        instruction += f"\n\nVoice Reply Instruction:\n{VOICE_REPLY_INSTRUCTION}"
    return instruction

def _call_gemini(user_prompt: str, chat_history: list = None, custom_instruction: Optional[str] = None) -> str:
    """Executes call to Google GenAI Gemini model with a 10s deadline."""
    active_client = client or get_gemini_client()
    if not active_client:
        raise ValueError("GEMINI_API_KEY missing or client unavailable")

    model_name = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL

    formatted_contents = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg.get("role") == "user" else "model"
            formatted_contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
            )
    formatted_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
    )

    system_inst = custom_instruction or build_system_instruction(user_prompt)
    response = active_client.models.generate_content(
        model=model_name,
        contents=formatted_contents,
        config=types.GenerateContentConfig(
            system_instruction=system_inst,
            temperature=0.2,
            http_options=types.HttpOptions(timeout=10000),
        ),
    )
    if response and response.text:
        return response.text.strip()
    return "I processed your request, but received an empty response from Gemini."

def _call_groq(user_prompt: str, chat_history: list = None, custom_instruction: Optional[str] = None) -> str:
    """Executes fallback call to Groq API with 10s timeout."""
    active_groq = groq_client or get_groq_client()
    if not active_groq:
        raise ValueError("GROQ_API_KEY missing or client unavailable")

    model_name = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL

    system_inst = custom_instruction or build_system_instruction(user_prompt)
    messages = [{"role": "system", "content": system_inst}]
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_prompt})

    completion = active_groq.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2,
        max_tokens=1024,
        timeout=10.0,
    )
    if completion and completion.choices and len(completion.choices) > 0:
        content = completion.choices[0].message.content
        if content:
            return content.strip()
    return "I processed your request with Groq, but received an empty response."

def _stream_groq(user_prompt: str, chat_history: list = None, custom_instruction: Optional[str] = None):
    """Executes streaming call to Groq API with 10s timeout."""
    active_groq = groq_client or get_groq_client()
    if not active_groq:
        raise ValueError("GROQ_API_KEY missing or client unavailable")

    model_name = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
    system_inst = custom_instruction or build_system_instruction(user_prompt)
    messages = [{"role": "system", "content": system_inst}]
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_prompt})

    completion = active_groq.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.2,
        max_tokens=1024,
        timeout=10.0,
        stream=True,
    )
    for chunk in completion:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

def _stream_gemini(user_prompt: str, chat_history: list = None, custom_instruction: Optional[str] = None):
    """Executes streaming call to Google GenAI Gemini model with 10s deadline."""
    active_client = client or get_gemini_client()
    if not active_client:
        raise ValueError("GEMINI_API_KEY missing or client unavailable")

    model_name = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
    formatted_contents = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg.get("role") == "user" else "model"
            formatted_contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
            )
    formatted_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
    )

    system_inst = custom_instruction or build_system_instruction(user_prompt)
    response = active_client.models.generate_content_stream(
        model=model_name,
        contents=formatted_contents,
        config=types.GenerateContentConfig(
            system_instruction=system_inst,
            temperature=0.2,
            http_options=types.HttpOptions(timeout=10000),
        ),
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text

async def _run_stream_in_thread(sync_gen_fn, *args):
    """Runs a synchronous generator in a thread feeding a queue to avoid event-loop blocking."""
    q = queue.Queue()
    _DONE = object()

    def worker():
        try:
            for item in sync_gen_fn(*args):
                q.put(item)
            q.put(_DONE)
        except Exception as e:
            q.put(e)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = await asyncio.to_thread(q.get)
        if item is _DONE:
            break
        if isinstance(item, Exception):
            raise item
        yield item

def _format_error_log(provider: str, err: Exception) -> str:
    """Format safe provider failure log without exposing secrets, request bodies, or error payloads."""
    status = getattr(err, "status_code", getattr(err, "code", getattr(err, "http_status", None)))
    status_str = f" status={status}" if status is not None else ""
    return f"[LLM] {provider} failed: {type(err).__name__}{status_str}"

def process_jarvis_intent(user_prompt: str, chat_history: list = None, is_voice: bool = False) -> dict:
    """
    Core intent routing chain:
    1. Local regex router (0ms local execution)
    2. Primary Cloud LLM (Groq with 10s timeout)
    3. Fallback Cloud LLM (Google Gemini with 10s timeout)
    4. Safe spoken error message (never crashes the request)
    5. Reply language guard: retries once if wrong script, then falls back to English with short note
    """
    # 1. 0ms Fast-Path Local Router
    handled, result = fast_path_local_router(user_prompt)
    if handled:
        print("[LLM Engine] Provider: Local Regex Router")
        return result

    expected_lang = detect_reply_language(user_prompt)

    def _execute_cloud_call(prompt: str, instruction: str) -> tuple[Optional[str], Optional[str]]:
        # 2. Primary: Groq Cloud Core (10s timeout)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and groq_key.strip():
            try:
                reply = _call_groq(prompt, chat_history, custom_instruction=instruction)
                model_name = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
                print(f"[LLM Engine] Provider: Groq ({model_name})")
                return reply, f"Groq ({model_name})"
            except Exception as groq_err:
                print(_format_error_log("groq", groq_err))
        else:
            print("[LLM] groq failed: ValueError status=missing_key")

        # 3. Fallback: Google Gemini Cloud Core (10s timeout)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and gemini_key.strip():
            try:
                reply = _call_gemini(prompt, chat_history, custom_instruction=instruction)
                model_name = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
                print(f"[LLM Engine] Provider: Gemini ({model_name}) [Fallback]")
                return reply, f"Gemini ({model_name}) Fallback"
            except Exception as gemini_err:
                print(_format_error_log("gemini", gemini_err))
        else:
            print("[LLM] gemini failed: ValueError status=missing_key")

        return None, None

    # Initial call with dynamic system instruction
    init_inst = build_system_instruction(user_prompt, is_voice=is_voice)
    reply, tool_name = _execute_cloud_call(user_prompt, init_inst)

    if reply is None:
        return {
            "reply": "I am having trouble connecting to cloud services right now. Please check your internet connection or API keys.",
            "tool_executed": None
        }

    # Language Guard: verify reply script matches expected_lang
    if not is_valid_script_reply(reply, expected_lang):
        script_name = "Kannada script" if expected_lang == "kannada" else ("Devanagari" if expected_lang == "hindi" else "Latin")
        retry_inst = f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\nReply only in {expected_lang.title()}. Use only {script_name} characters."
        if is_voice:
            retry_inst += f"\n\nVoice Reply Instruction:\n{VOICE_REPLY_INSTRUCTION}"
        reply_retry, tool_retry = _execute_cloud_call(user_prompt, retry_inst)

        if reply_retry and is_valid_script_reply(reply_retry, expected_lang):
            return {"reply": reply_retry, "tool_executed": f"{tool_retry or tool_name} (Language Guard Retry)"}

        # If still wrong, reply in English and add a short English note that the requested language could not be used
        eng_inst = f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\nReply in English."
        if is_voice:
            eng_inst += f"\n\nVoice Reply Instruction:\n{VOICE_REPLY_INSTRUCTION}"
        eng_reply, eng_tool = _execute_cloud_call(user_prompt, eng_inst)
        if not eng_reply:
            eng_reply = "I could not complete your request at this time."
        fallback_note = f"Note: Could not respond in {expected_lang.title()} as requested. {eng_reply}"
        return {"reply": fallback_note, "tool_executed": f"{eng_tool or tool_name} (English Fallback)"}

    return {"reply": reply, "tool_executed": tool_name}

async def process_jarvis_intent_async(user_prompt: str, chat_history: list = None, is_voice: bool = False) -> dict:
    """Non-blocking async wrapper that offloads blocking SDK calls to a worker thread."""
    return await asyncio.to_thread(process_jarvis_intent, user_prompt, chat_history, is_voice)
    """Non-blocking async wrapper that offloads blocking SDK calls to a worker thread."""
    return await asyncio.to_thread(process_jarvis_intent, user_prompt, chat_history)

async def _stream_from_providers(prompt: str, instruction: str, chat_history: list = None, cancel_event: Optional[asyncio.Event] = None, request_start_time: Optional[float] = None):
    groq_key = os.getenv("GROQ_API_KEY")
    chunks_yielded = 0
    if groq_key and groq_key.strip():
        try:
            model_name = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
            provider_logged = False
            async for chunk in _run_stream_in_thread(_stream_groq, prompt, chat_history, instruction):
                if cancel_event and cancel_event.is_set():
                    return
                if not provider_logged:
                    print(f"[LLM Engine] Provider: Groq ({model_name})")
                    provider_logged = True
                if chunks_yielded == 0 and request_start_time is not None and os.getenv("DEBUG_TIMING", "0") == "1":
                    token_ms = (time.perf_counter() - request_start_time) * 1000
                    print(f"[TIMING] Time to first LLM token: {token_ms:.1f}ms", flush=True)
                chunks_yielded += 1
                yield chunk
            return
        except Exception as groq_err:
            print(_format_error_log("groq", groq_err))
            if chunks_yielded > 0:
                return
    else:
        print("[LLM] groq failed: ValueError status=missing_key")

    if cancel_event and cancel_event.is_set():
        return

    if chunks_yielded == 0:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and gemini_key.strip():
            try:
                model_name = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
                provider_logged = False
                async for chunk in _run_stream_in_thread(_stream_gemini, prompt, chat_history, instruction):
                    if cancel_event and cancel_event.is_set():
                        return
                    if not provider_logged:
                        print(f"[LLM Engine] Provider: Gemini ({model_name}) [Fallback]")
                        provider_logged = True
                    if chunks_yielded == 0 and request_start_time is not None and os.getenv("DEBUG_TIMING", "0") == "1":
                        token_ms = (time.perf_counter() - request_start_time) * 1000
                        print(f"[TIMING] Time to first LLM token: {token_ms:.1f}ms", flush=True)
                    chunks_yielded += 1
                    yield chunk
                return
            except Exception as gemini_err:
                print(_format_error_log("gemini", gemini_err))
                if chunks_yielded > 0:
                    return
        else:
            print("[LLM] gemini failed: ValueError status=missing_key")

    if chunks_yielded == 0 and (not cancel_event or not cancel_event.is_set()):
        yield "I am having trouble connecting to cloud services right now. Please check your internet connection or API keys."

async def process_jarvis_intent_stream(
    user_prompt: str,
    chat_history: list = None,
    cancel_event: Optional[asyncio.Event] = None,
    request_start_time: Optional[float] = None,
    is_voice: bool = False
):
    """
    Yields text chunks with streaming intent routing and language guard:
    1. Local regex router (0ms local execution, yields reply as single chunk)
    2. Primary: Groq streaming (10s timeout)
    3. Fallback: Google Gemini streaming (10s timeout, if Groq fails before yielding)
    4. Safe spoken error fallback
    5. Language guard: verifies first sentence script matches expected language; retries once if wrong, then English fallback
    """
    if cancel_event and cancel_event.is_set():
        return

    # 1. 0ms Fast-Path Local Router
    handled, result = fast_path_local_router(user_prompt)
    if handled:
        print("[LLM Engine] Provider: Local Regex Router")
        yield result.get("reply", "")
        return

    expected_lang = detect_reply_language(user_prompt)
    init_inst = build_system_instruction(user_prompt, is_voice=is_voice)

    # Validate first sentence script before emitting wrong-script speech
    buffered_chunks = []
    buffered_text = ""
    stream_wrong = False

    async for chunk in _stream_from_providers(user_prompt, init_inst, chat_history, cancel_event, request_start_time):
        if cancel_event and cancel_event.is_set():
            return
        buffered_chunks.append(chunk)
        buffered_text += chunk
        if any(p in chunk for p in (".", "!", "?", "।", "\n")) or len(buffered_text) >= 25:
            if not is_valid_script_reply(buffered_text, expected_lang):
                stream_wrong = True
                break
            else:
                for b in buffered_chunks:
                    yield b
                buffered_chunks = []
                buffered_text = ""

    if buffered_chunks and not stream_wrong:
        if is_valid_script_reply(buffered_text, expected_lang):
            for b in buffered_chunks:
                yield b
            return
        else:
            stream_wrong = True

    # If wrong script, retry once with explicit constraint
    if stream_wrong and (not cancel_event or not cancel_event.is_set()):
        script_name = "Kannada script" if expected_lang == "kannada" else ("Devanagari" if expected_lang == "hindi" else "Latin")
        retry_inst = f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\nReply only in {expected_lang.title()}. Use only {script_name} characters."
        if is_voice:
            retry_inst += f"\n\nVoice Reply Instruction:\n{VOICE_REPLY_INSTRUCTION}"

        retry_chunks = []
        retry_text = ""
        retry_wrong = False

        async for chunk in _stream_from_providers(user_prompt, retry_inst, chat_history, cancel_event, request_start_time):
            if cancel_event and cancel_event.is_set():
                return
            retry_chunks.append(chunk)
            retry_text += chunk
            if any(p in chunk for p in (".", "!", "?", "।", "\n")) or len(retry_text) >= 25:
                if not is_valid_script_reply(retry_text, expected_lang):
                    retry_wrong = True
                    break
                else:
                    for b in retry_chunks:
                        yield b
                    retry_chunks = []
                    retry_text = ""

        if retry_chunks and not retry_wrong:
            if is_valid_script_reply(retry_text, expected_lang):
                for b in retry_chunks:
                    yield b
                return
            else:
                retry_wrong = True

        # If still wrong, fallback to English with a short note
        if retry_wrong and (not cancel_event or not cancel_event.is_set()):
            yield f"Note: Could not respond in {expected_lang.title()} as requested. "
            eng_inst = f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\nReply in English."
            if is_voice:
                eng_inst += f"\n\nVoice Reply Instruction:\n{VOICE_REPLY_INSTRUCTION}"
            async for chunk in _stream_from_providers(user_prompt, eng_inst, chat_history, cancel_event, request_start_time):
                if cancel_event and cancel_event.is_set():
                    return
                yield chunk

def click_at_coordinates(x: int, y: int) -> str:
    """Clicks directly on desktop screen coordinates (x, y)."""
    try:
        pyautogui.click(x=x, y=y)
        return f"Clicked targeted screen coordinates ({x}, {y})"
    except Exception as e:
        return f"Failed to click coordinates ({x}, {y}): {str(e)}"

def click_bounding_box(box_index: int, bounding_boxes: list) -> str:
    """Calculates center of target OpenCV bounding box and clicks it."""
    try:
        if 0 <= box_index < len(bounding_boxes):
            box = bounding_boxes[box_index]
            center_x = box["x"] + (box["w"] // 2)
            center_y = box["y"] + (box["h"] // 2)
            pyautogui.click(x=center_x, y=center_y)
            return f"Targeted UI box #{box_index}: Clicked at center ({center_x}, {center_y})"
        return f"Invalid bounding box index: {box_index}"
    except Exception as e:
        return f"Visual click failed: {str(e)}"
