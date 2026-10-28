import os
import re
import subprocess
import asyncio
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
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"  # Verify in https://ai.google.dev/gemini-api/docs/models
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"  # Verify in https://console.groq.com/docs/models

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

def _call_gemini(user_prompt: str, chat_history: list = None) -> str:
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

    response = active_client.models.generate_content(
        model=model_name,
        contents=formatted_contents,
        config=types.GenerateContentConfig(
            system_instruction=JARVIS_SYSTEM_INSTRUCTION,
            temperature=0.2,
            http_options=types.HttpOptions(timeout=10000),
        ),
    )
    if response and response.text:
        return response.text.strip()
    return "I processed your request, but received an empty response from Gemini."

def _call_groq(user_prompt: str, chat_history: list = None) -> str:
    """Executes fallback call to Groq API with 10s timeout."""
    active_groq = groq_client or get_groq_client()
    if not active_groq:
        raise ValueError("GROQ_API_KEY missing or client unavailable")

    model_name = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL

    messages = [{"role": "system", "content": JARVIS_SYSTEM_INSTRUCTION}]
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

def process_jarvis_intent(user_prompt: str, chat_history: list = None) -> dict:
    """
    Core intent routing chain:
    1. Local regex router (0ms local execution)
    2. Primary Cloud LLM (Google Gemini with 10s timeout)
    3. Fallback Cloud LLM (Groq if GEMINI fails and GROQ_API_KEY is configured)
    4. Safe spoken error message (never crashes the request)
    """
    # 1. 0ms Fast-Path Local Router
    handled, result = fast_path_local_router(user_prompt)
    if handled:
        print("[LLM Engine] Provider: Local Regex Router")
        return result

    # 2. Primary: Google Gemini Cloud Core
    try:
        reply = _call_gemini(user_prompt, chat_history)
        model_name = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
        print(f"[LLM Engine] Provider: Gemini ({model_name})")
        return {"reply": reply, "tool_executed": f"Gemini ({model_name})"}
    except Exception as err:
        # Never log API keys or secrets
        print(f"[LLM Engine] Gemini call failed: {type(err).__name__}. Evaluating Groq fallback...")

    # 3. Fallback: Groq Cloud Core (if GROQ_API_KEY is configured)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.strip():
        try:
            reply = _call_groq(user_prompt, chat_history)
            model_name = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
            print(f"[LLM Engine] Provider: Groq ({model_name}) [Fallback]")
            return {"reply": reply, "tool_executed": f"Groq ({model_name}) Fallback"}
        except Exception as groq_err:
            # Never log API keys or secrets
            print(f"[LLM Engine] Groq fallback failed: {type(groq_err).__name__}")

    # 4. Graceful spoken error fallback (Never crash the request)
    return {
        "reply": "I am having trouble connecting to cloud services right now. Please check your internet connection or API keys.",
        "tool_executed": None
    }

async def process_jarvis_intent_async(user_prompt: str, chat_history: list = None) -> dict:
    """Non-blocking async wrapper that offloads blocking SDK calls to a worker thread."""
    return await asyncio.to_thread(process_jarvis_intent, user_prompt, chat_history)

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
