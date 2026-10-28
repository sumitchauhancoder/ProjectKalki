import os
import re
import subprocess
import asyncio
import threading
import queue
import time
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

def build_system_instruction(user_prompt: str) -> str:
    """Builds dynamic system prompt embedding detected reply language instruction."""
    lang = detect_reply_language(user_prompt)
    lang_instruction = get_language_instruction(lang)
    return f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\n{lang_instruction}"

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

def process_jarvis_intent(user_prompt: str, chat_history: list = None) -> dict:
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
    init_inst = build_system_instruction(user_prompt)
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
        reply_retry, tool_retry = _execute_cloud_call(user_prompt, retry_inst)

        if reply_retry and is_valid_script_reply(reply_retry, expected_lang):
            return {"reply": reply_retry, "tool_executed": f"{tool_retry or tool_name} (Language Guard Retry)"}

        # If still wrong, reply in English and add a short English note that the requested language could not be used
        eng_inst = f"{JARVIS_SYSTEM_INSTRUCTION.strip()}\n\nExplicit Language Instruction:\nReply in English."
        eng_reply, eng_tool = _execute_cloud_call(user_prompt, eng_inst)
        if not eng_reply:
            eng_reply = "I could not complete your request at this time."
        fallback_note = f"Note: Could not respond in {expected_lang.title()} as requested. {eng_reply}"
        return {"reply": fallback_note, "tool_executed": f"{eng_tool or tool_name} (English Fallback)"}

    return {"reply": reply, "tool_executed": tool_name}

async def process_jarvis_intent_async(user_prompt: str, chat_history: list = None) -> dict:
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
    request_start_time: Optional[float] = None
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
    init_inst = build_system_instruction(user_prompt)

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
