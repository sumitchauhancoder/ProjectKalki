import os
import re
import subprocess
import pyautogui
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

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
    """Launches desktop application locally."""
    clean_name = app_name.lower().strip()
    target = APP_MAP.get(clean_name, clean_name)
    try:
        subprocess.Popen(target, shell=True)
        return f"Launched {app_name}"
    except Exception as e:
        return f"Failed to launch {app_name}: {str(e)}"

def fast_path_local_router(user_prompt: str):
    """
    Executes instant local OS automations in 0ms without hitting Cloud API.
    Returns (handled: bool, result_dict: dict)
    """
    prompt = user_prompt.lower().strip()

    # Pattern 1: Open / Launch / Start <app>
    match = re.search(r'\b(open|launch|start|run)\s+(now\s+)?([a-z0-9\s]+)', prompt)
    if match:
        target_app = match.group(3).strip()
        for app_key in APP_MAP.keys():
            if app_key in target_app:
                res = launch_application(app_key)
                return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}
        
        # Generic launch fallback
        res = launch_application(target_app)
        return True, {"reply": res, "tool_executed": f"Fast-Path Local: {res}"}

    # Pattern 2: Type / Write <text>
    if prompt.startswith("type ") or prompt.startswith("write "):
        text_to_type = prompt.split(" ", 1)[1]
        pyautogui.write(text_to_type, interval=0.01)
        return True, {"reply": f"Typed: '{text_to_type}'", "tool_executed": "Fast-Path Local: type_text"}

    return False, None

JARVIS_SYSTEM_INSTRUCTION = """
You are KALKI, an autonomous J.A.R.V.I.S.-style AI core assistant.
You assist the user with OS automation, system tasks, and technical queries.

Rules:
1. Speak concisely, clearly, and directly—like a high-performance AI system core.
2. If the user asks to perform an OS action, execute the available tools immediately.
3. If no tool is needed, respond with clear technical reasoning.
"""

def process_jarvis_intent(user_prompt: str) -> dict:
    # 1. Check Fast-Path Local Execution (0ms)
    handled_locally, local_result = fast_path_local_router(user_prompt)
    if handled_locally:
        return local_result

    # 2. Fallback to Cloud LLM Reasoner for complex prompts
    if not client:
        return {
            "reply": "API key missing. Add GEMINI_API_KEY to your .env file.",
            "tool_executed": None
        }

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=JARVIS_SYSTEM_INSTRUCTION,
                tools=[launch_application],
                temperature=0.2,
            ),
        )

        executed_actions = []

        if response.function_calls:
            for call in response.function_calls:
                if call.name == "launch_application":
                    res = launch_application(call.args.get("app_name", ""))
                    executed_actions.append(res)

        reply_text = response.text if response.text else (
            f"Executed: {', '.join(executed_actions)}" if executed_actions else "Command completed."
        )

        return {
            "reply": reply_text,
            "tool_executed": ", ".join(executed_actions) if executed_actions else None
        }

    except Exception as e:
        return {
            "reply": f"Jarvis Core Error: {str(e)}",
            "tool_executed": None
        }