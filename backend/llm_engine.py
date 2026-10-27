import os
import re
import subprocess
import pyautogui
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env explicitly from the backend/ folder relative to this file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv("GEMINI_API_KEY")
client = (
    genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=10000))
    if api_key and api_key.strip() != ""
    else None
)

APP_MAP = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "vs code": "code",
    "vscode": "code",
    "code": "code",
    "chrome": "start chrome",
    "browser": "start https://google.com"
}

def launch_application(app_name: str) -> str:
    clean_name = app_name.lower().strip()
    target = APP_MAP.get(clean_name, clean_name)
    try:
        subprocess.Popen(target, shell=True)
        return f"Launched {app_name}"
    except Exception as e:
        return f"Failed to launch {app_name}: {str(e)}"

def fast_path_local_router(user_prompt: str):
    """0ms Instant local execution."""
    prompt = user_prompt.lower().strip()

    if prompt in ["who are you", "who are you?", "what is your name", "what is your name?"]:
        return True, {
            "reply": "I am KALKI, your autonomous multi-lingual desktop AI core assistant.",
            "tool_executed": "Local Identity Engine"
        }

    match = re.search(r'\b(open|launch|start|run)\s+(now\s+)?([a-z0-9\s]+)', prompt)
    if match:
        target_app = match.group(3).strip()
        for app_key in APP_MAP.keys():
            if app_key in target_app:
                res = launch_application(app_key)
                return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}
        res = launch_application(target_app)
        return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}

    if prompt.startswith("type ") or prompt.startswith("write "):
        text_to_type = prompt.split(" ", 1)[1]
        pyautogui.write(text_to_type, interval=0.01)
        return True, {"reply": f"Typed: '{text_to_type}'", "tool_executed": "Fast-Path Local: type_text"}

    return False, None

JARVIS_SYSTEM_INSTRUCTION = """
You are KALKI, an autonomous multi-lingual J.A.R.V.I.S.-style AI core assistant.
Rules:
1. Detect user language (English, Kannada, Hindi, Kanglish) and respond naturally in the same language.
2. Keep responses brief, sharp, concise, and authoritative.
3. Provide direct answers to general knowledge questions.
"""

def process_jarvis_intent(user_prompt: str) -> dict:
    # 1. 0ms Fast-Path Local Router
    handled, result = fast_path_local_router(user_prompt)
    if handled:
        return result

    # 2. Cloud Gemini LLM Core
    if client:
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=JARVIS_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    http_options=types.HttpOptions(timeout=10000),
                ),
            )
            reply_text = response.text.strip() if response.text else "No content returned from model."
            return {"reply": reply_text, "tool_executed": "Gemini 3.8 Flash Core"}
        except TimeoutError as te:
            print(f"[Gemini API Timeout]: {str(te)}")
            return {
                "reply": "Cloud Core request timed out. Please try again.",
                "tool_executed": None
            }
        except Exception as err:
            err_msg = str(err)
            print(f"[Gemini API Error]: {err_msg}")
            if "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
                return {
                    "reply": "Cloud Core request timed out. Please check your connection.",
                    "tool_executed": None
                }
            return {
                "reply": f"Cloud Core Error: {err_msg}",
                "tool_executed": None
            }

    print(f"[Warning]: GEMINI_API_KEY is missing or invalid in {env_path}")
    return {
        "reply": f"GEMINI_API_KEY is missing in backend/.env file. Please set a valid key.",
        "tool_executed": None
    }
