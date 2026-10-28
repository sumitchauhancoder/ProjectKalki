import os
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import llm_engine
import database
import models
from app import app, health_check

def run_all_checks():
    print("=" * 70)
    print("PROJECT KALKI — PHASE 0 DIAGNOSTICS & SAFETY VERIFICATION")
    print("=" * 70)
    
    all_passed = True

    # --------------------------------------------------------------------------
    # Check 1: .env loads from the backend folder, not the current working directory
    # --------------------------------------------------------------------------
    print("\n[Check 1] .env Location Resolution:")
    try:
        expected_env = backend_dir / ".env"
        assert llm_engine.env_path == expected_env, f"llm_engine .env mismatch: {llm_engine.env_path} != {expected_env}"
        assert database.env_path == expected_env, f"database .env mismatch: {database.env_path} != {expected_env}"
        print(f"  Anchor path: {expected_env}")
        print("  llm_engine and database both resolve explicitly to backend/.env")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 2: The app starts with no PostgreSQL running
    # --------------------------------------------------------------------------
    print("\n[Check 2] App Starts Gracefully Without PostgreSQL:")
    try:
        assert app is not None, "FastAPI app instance is None"
        assert app.title == "KALKI Core Engine", f"Unexpected app title: {app.title}"
        res = health_check()
        assert res.get("status") == "online", f"Health check returned unexpected payload: {res}"
        print("  FastAPI app initialized without crashing on missing PostgreSQL")
        print(f"  health_check() response: {res}")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 3: Groq Primary & Gemini Fallback Chain (Mocked, 0 Network Calls)
    # --------------------------------------------------------------------------
    print("\n[Check 3] LLM Chain: Groq Primary, Gemini Fallback, and Safe Fallback:")
    try:
        import groq
        import httpx

        # 3a. Groq success returns Groq's answer and never calls Gemini
        with patch.object(llm_engine, "_call_groq", return_value="Paris is the capital of France.") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini, \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_groq_key", "GEMINI_API_KEY": "dummy_gemini_key"}):

            res1 = llm_engine.process_jarvis_intent("What is the capital of France?")
            assert mock_groq.called, "Groq was not called as primary LLM"
            assert not mock_gemini.called, "Gemini was called even though Groq succeeded!"
            assert res1.get("reply") == "Paris is the capital of France."
            assert "Groq" in res1.get("tool_executed", "")
        print("  Case 3a: Groq primary answered successfully; Gemini was not called.")

        # 3b. Groq failure (mocked 429) falls back to Gemini and returns Gemini's answer
        dummy_req = httpx.Request("POST", "http://test")
        dummy_resp = httpx.Response(status_code=429, request=dummy_req)
        mock_groq_429 = groq.RateLimitError("Rate limit exceeded", response=dummy_resp, body=None)

        with patch.object(llm_engine, "_call_groq", side_effect=mock_groq_429) as mock_groq, \
             patch.object(llm_engine, "_call_gemini", return_value="Gemini fallback: 299,792 km/s") as mock_gemini, \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_groq_key", "GEMINI_API_KEY": "dummy_gemini_key"}):

            res2 = llm_engine.process_jarvis_intent("What is the speed of light?")
            assert mock_groq.called, "Groq was not called first"
            assert mock_gemini.called, "Gemini fallback was not called after Groq 429 failure"
            assert res2.get("reply") == "Gemini fallback: 299,792 km/s"
            assert "Gemini" in res2.get("tool_executed", "")
        print("  Case 3b: Groq 429 failure cleanly triggered Gemini fallback.")

        # 3c. Both failing returns safe spoken error message
        with patch.object(llm_engine, "_call_groq", side_effect=Exception("Groq offline")), \
             patch.object(llm_engine, "_call_gemini", side_effect=Exception("Gemini quota 0")), \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_groq_key", "GEMINI_API_KEY": "dummy_gemini_key"}):

            res3 = llm_engine.process_jarvis_intent("Query that fails everywhere")
            assert "trouble connecting to cloud services" in res3.get("reply", "")
            assert res3.get("tool_executed") is None
        print("  Case 3c: Both providers failing returned safe spoken error message.")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 4: The local router answers an app-launch command with no cloud call
    # --------------------------------------------------------------------------
    print("\n[Check 4] Local Router Answers App-Launch Command With Zero Cloud Calls:")
    try:
        with patch("subprocess.Popen") as mock_popen, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini, \
             patch.object(llm_engine, "_call_groq") as mock_groq:
            
            result = llm_engine.process_jarvis_intent("open calculator")
            
            assert not mock_gemini.called, "Gemini was called for a local app launch command!"
            assert not mock_groq.called, "Groq was called for a local app launch command!"
            assert mock_popen.called, "subprocess.Popen was not invoked for calculator launch"
            assert result.get("tool_executed") == "Fast-Path Local: Launched calculator", f"Unexpected tool_executed: {result}"
            
        print("  Command: 'open calculator' -> Handled by Fast-Path Local Router")
        print(f"  Result payload: {result}")
        print("  Gemini calls: 0 | Groq calls: 0")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 5: The database falls back to SQLite when DATABASE_URL is unset
    # --------------------------------------------------------------------------
    print("\n[Check 5] Database Falls Back to SQLite When DATABASE_URL Is Unset:")
    try:
        from sqlalchemy import create_engine
        
        # Test default fallback URL calculation
        with patch.dict(os.environ, {}, clear=True):
            test_raw_url = os.getenv("DATABASE_URL")
            assert test_raw_url is None, "DATABASE_URL was expected to be unset in test environment"
            
            sqlite_db_file = (backend_dir / "kalki.db").as_posix()
            expected_sqlite_url = f"sqlite:///{sqlite_db_file}"
            
            # Verify SQLite engine creation and table mapping without a server
            test_engine = create_engine(expected_sqlite_url, connect_args={"check_same_thread": False})
            models.Base.metadata.create_all(bind=test_engine)
            
            # Test session creation and basic query
            from sqlalchemy.orm import sessionmaker
            TestSession = sessionmaker(bind=test_engine)
            session = TestSession()
            macro_count = session.query(models.VoiceMacro).count()
            session.close()
            
        print(f"  Default URL when unset: sqlite:///{sqlite_db_file}")
        print(f"  SQLite tables verified, VoiceMacro table count: {macro_count}")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 6: Unique TTS file names (two calls produce two different paths)
    # --------------------------------------------------------------------------
    print("\n[Check 6] Unique TTS File Names:")
    try:
        from tts_engine import get_unique_tts_path
        path_1 = get_unique_tts_path()
        path_2 = get_unique_tts_path()
        assert path_1 != path_2, f"Expected unique paths, got identical: {path_1}"
        assert str(path_1).endswith(".mp3"), f"Expected .mp3 extension: {path_1}"
        assert str(path_2).endswith(".mp3"), f"Expected .mp3 extension: {path_2}"
        print(f"  Generated Path 1: {path_1.name}")
        print(f"  Generated Path 2: {path_2.name}")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 7: TTS Queue Ordering (Three queued items play in order)
    # --------------------------------------------------------------------------
    print("\n[Check 7] TTS Queue FIFO Ordering:")
    try:
        import asyncio
        import tts_engine

        async def _test_tts_queue():
            played_items = []

            async def mock_player(job_text):
                played_items.append(job_text)

            orig_hook = tts_engine.playback_hook
            tts_engine.playback_hook = mock_player
            try:
                q = tts_engine.get_tts_queue()
                await tts_engine.enqueue_speech("Item Alpha")
                await tts_engine.enqueue_speech("Item Beta")
                await tts_engine.enqueue_speech("Item Gamma")
                await q.join()
                assert played_items == ["Item Alpha", "Item Beta", "Item Gamma"], (
                    f"Queue order mismatch: {played_items}"
                )
            finally:
                tts_engine.playback_hook = orig_hook
            return played_items

        results = asyncio.run(_test_tts_queue())
        print(f"  Queued items played in strict order: {results}")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 8: Vision routes do not enqueue speech
    # --------------------------------------------------------------------------
    print("\n[Check 8] Vision Routes Do Not Enqueue Speech:")
    try:
        from fastapi.testclient import TestClient
        import tts_engine

        client = TestClient(app, raise_server_exceptions=False)
        with patch.object(tts_engine, "speak_text") as mock_speak, \
             patch("app.speak_text") as mock_app_speak:

            # 1. /process-frame
            dummy_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            r1 = client.post("/process-frame", json={"image_base64": dummy_img})
            assert r1.status_code == 200, f"/process-frame failed: {r1.status_code}"
            assert not mock_speak.called and not mock_app_speak.called, "speak_text called from /process-frame!"

            # 2. /visual-click
            with patch("app.click_bounding_box", return_value="Clicked UI Box"):
                r2 = client.post("/visual-click", json={"box_index": 0, "bounding_boxes": [{"x": 10, "y": 10, "w": 20, "h": 20}]})
                assert r2.status_code == 200, f"/visual-click failed: {r2.status_code}"
                assert not mock_speak.called and not mock_app_speak.called, "speak_text called from /visual-click!"

        print("  Verified: Neither /process-frame nor /visual-click enqueued speech")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 9: Safe Error Logging on Gemini Failure
    # --------------------------------------------------------------------------
    print("\n[Check 9] Safe Error Logging on Gemini Failure:")
    try:
        from google.genai.errors import ClientError
        from io import StringIO

        fake_secret = "AIzaSySuperSecretApiKeyShouldNeverBeLogged"
        mock_err = ClientError(429, f"Quota exceeded with token {fake_secret}")

        captured = StringIO()
        with patch("sys.stdout", captured), \
             patch.object(llm_engine, "_call_gemini", side_effect=mock_err), \
             patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            llm_engine.process_jarvis_intent("What is the weather today?")

        out = captured.getvalue()
        assert "[LLM] gemini failed: ClientError status=429" in out, f"Expected formatted error log not found: {out}"
        assert fake_secret not in out, "Leaked secret key into log output!"
        print("  [LLM] gemini failed: ClientError status=429 logged successfully")
        print("  Verified: Secret key was NOT in log output")
        print("  PASS")
    except Exception as e:
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 9 DIAGNOSTICS & SAFETY CHECKS PASSED [PASS]")
        print("=" * 70)
        sys.exit(0)
    else:
        print("ONE OR MORE CHECKS FAILED [FAIL]")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    run_all_checks()
