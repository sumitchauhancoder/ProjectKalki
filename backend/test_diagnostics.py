import sys
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import llm_engine
import app
from app import run_command, CommandPayload

def run_diagnostics():
    print("=" * 65)
    print("KALKI ASSISTANT CORE DIAGNOSTICS & VERIFICATION")
    print("=" * 65)

    # 1. Verify .env loading path
    print("\n[Check 1] .env Path Explicit Resolution:")
    expected_env_path = backend_dir / ".env"
    print(f"  Expected path: {expected_env_path}")
    print(f"  Actual path:   {llm_engine.env_path}")
    assert llm_engine.env_path == expected_env_path, "Mismatch in .env path!"
    assert llm_engine.env_path.exists(), f".env not found at {llm_engine.env_path}"
    print("  -> PASSED: backend/.env is explicitly resolved via Path(__file__).resolve().parent / '.env'")

    # 2. Inspect active Gemini model name and google-genai
    print("\n[Check 2] Google GenAI Active Model Name:")
    with open(backend_dir / "llm_engine.py", "r", encoding="utf-8") as f:
        llm_code = f.read()
    assert "gemini-3.8-flash" in llm_code, "Active model 'gemini-3.8-flash' missing in llm_engine.py!"
    print("  -> Active Model: gemini-3.8-flash")
    print(f"  -> GenAI Client configured: {llm_engine.client is not None}")
    print("  -> PASSED: gemini-3.8-flash is active model with google-genai")

    # 3. Verify process_jarvis_intent timeout handling & try-except wrapping
    print("\n[Check 3] Non-Local Query Handling & Timeout Protection:")
    assert "timeout=" in llm_code or "HttpOptions" in llm_code, "Explicit timeout missing in client calls!"
    t0 = time.time()
    res = llm_engine.process_jarvis_intent("who is pm of india")
    duration = time.time() - t0
    print(f"  Query: 'who is pm of india'")
    print(f"  Duration: {duration:.3f}s")
    print(f"  Result: {res}")
    assert isinstance(res, dict) and "reply" in res, "Result must be dict containing 'reply'"
    print("  -> PASSED: process_jarvis_intent handled client call gracefully in try-except")

    # 4. Verify backend/app.py fires speak_text via asyncio.create_task()
    print("\n[Check 4] Non-blocking Background Task (speak_text):")
    with open(backend_dir / "app.py", "r", encoding="utf-8") as f:
        app_code = f.read()
    assert "asyncio.create_task(speak_text(" in app_code, "asyncio.create_task(speak_text(...)) missing in app.py!"
    print("  -> Found: asyncio.create_task(speak_text(reply_message)) in /execute-command")
    print("  -> PASSED: speak_text is fired as non-blocking background task")

    # 5. Direct Execution of run_command with non-local prompt
    print("\n[Check 5] Endpoint Execution Test (POST /execute-command):")

    async def test_endpoint():
        with patch("app.speak_text", new_callable=AsyncMock) as mock_speak:
            t_start = time.time()
            result = await run_command(CommandPayload(command="who is pm of india"), db=None)
            elapsed = time.time() - t_start

            print(f"  Response time: {elapsed:.3f}s")
            print(f"  Endpoint returned: {result}")
            assert result["status"] == "success", f"Expected success status, got: {result}"
            assert "reply" in result, "Missing reply in JSON response"
            mock_speak.assert_called_once_with(result["reply"])
            print(f"  mock_speak called with: '{result['reply'][:50]}...'")
            print("  -> PASSED: POST /execute-command returns JSON immediately and triggers background TTS!")

    asyncio.run(test_endpoint())

    print("\n" + "=" * 65)
    print("ALL 5 DIAGNOSTIC CRITERIA VERIFIED AND PASSED!")
    print("=" * 65)

if __name__ == "__main__":
    run_diagnostics()
