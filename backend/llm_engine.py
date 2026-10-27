import os
import re
import subprocess
import pyautogui
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key and api_key.strip() != "" else None

groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key and groq_api_key.strip() != "" else None

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

def process_jarvis_intent(user_prompt: str, chat_history: list = None) -> dict:
    # 1. 0ms Fast-Path Local Router
    handled, result = fast_path_local_router(user_prompt)
    if handled:
        return result

    # 2. Try Cloud Gemini LLM Core first
    if client:
        try:
            formatted_contents = []
            if chat_history:
                for msg in chat_history:
                    role = "user" if msg["role"] == "user" else "model"
                    formatted_contents.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
                    )
            
            formatted_contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
            )

            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=formatted_contents,
                config=types.GenerateContentConfig(
                    system_instruction=JARVIS_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                ),
            )
            return {"reply": response.text.strip(), "tool_executed": "Gemini 3.8 Flash Core"}
        except Exception as err:
            print(f"[Gemini API Limit/Error]: {str(err)} -> Falling back to Groq Llama 3.3")

    # 3. Fallback to Groq Llama 3.3 if Gemini fails or hits quota limits
    # 3. Fallback to Groq if Gemini fails or hits quota limits
    if groq_client:
        try:
            messages = [{"role": "system", "content": JARVIS_SYSTEM_INSTRUCTION}]
            if chat_history:
                for msg in chat_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_prompt})

            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )
            reply_text = completion.choices[0].message.content.strip()
            return {"reply": reply_text, "tool_executed": "Groq GPT-OSS 120B Fallback Core"}
        except Exception as groq_err:
            print(f"[Groq API Error]: {str(groq_err)}")
            return {"reply": f"All Cloud Core Failovers Failed: {str(groq_err)}", "tool_executed": None}
    return {
        "reply": "Both GEMINI_API_KEY and GROQ_API_KEY are missing or exhausted in backend/.env.",
        "tool_executed": None
    }

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