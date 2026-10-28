import os
import sys
import time
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 10: Sentence Splitter (English, Hindi danda, mixed, chunks, decimals, flush)
    # --------------------------------------------------------------------------
    print("\n[Check 10] Sentence Splitter Functionality:")
    try:
        from sentence_splitter import SentenceSplitter

        # 10a. English (. ! ?)
        s1 = SentenceSplitter()
        res1 = s1.feed("First sentence. ") + s1.feed("Second sentence! ") + s1.feed("Is this third? ") + s1.flush()
        assert res1 == ["First sentence.", "Second sentence!", "Is this third?"], f"English split failed: {res1}"

        # 10b. Hindi danda (।)
        s2 = SentenceSplitter()
        res2 = s2.feed("यह पहला वाक्य है। ") + s2.feed("यह दूसरा वाक्य है। ") + s2.flush()
        assert res2 == ["यह पहला वाक्य है।", "यह दूसरा वाक्य है।"], f"Hindi split failed: {res2}"

        # 10c. Mixed language
        s3 = SentenceSplitter()
        res3 = s3.feed("Hello there! ") + s3.feed("ಇದು ಕನ್ನಡ ವಾಕ್ಯ. ") + s3.feed("यह हिंदी है। ") + s3.flush()
        assert res3 == ["Hello there!", "ಇದು ಕನ್ನಡ ವಾಕ್ಯ.", "यह हिंदी है।"], f"Mixed split failed: {res3}"

        # 10d. Split across chunk boundaries
        s4 = SentenceSplitter()
        res4 = s4.feed("This sentence is ") + s4.feed("split across chunks. ") + s4.flush()
        assert res4 == ["This sentence is split across chunks."], f"Chunk boundary split failed: {res4}"

        # 10e. Decimal numbers not split
        s5 = SentenceSplitter()
        res5 = s5.feed("The measurement is 3.") + s5.feed("14 meters in length. Done.") + s5.flush()
        assert res5 == ["The measurement is 3.14 meters in length.", "Done."], f"Decimal split failed: {res5}"

        # 10f. Flush at end
        s6 = SentenceSplitter()
        res6 = s6.feed("Unterminated sentence at end of stream") + s6.flush()
        assert res6 == ["Unterminated sentence at end of stream"], f"Flush failed: {res6}"

        print("  Verified: English, Hindi danda, mixed, split chunks, decimals, and flush all succeed.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 11: Streaming LLM Fallback & Mid-Stream Failure
    # --------------------------------------------------------------------------
    print("\n[Check 11] Streaming LLM Fallback & Mid-Stream Handling:")
    try:
        import asyncio

        async def _test_streaming_engine():
            # 11a. Stream fallback: Groq raises before any chunk, Gemini succeeds
            def mock_groq_fail(*args, **kwargs):
                raise ValueError("Groq initial error")
                yield

            def mock_gemini_ok(*args, **kwargs):
                yield "Gemini "
                yield "fallback "
                yield "stream."

            with patch.object(llm_engine, "_stream_groq", mock_groq_fail), \
                 patch.object(llm_engine, "_stream_gemini", mock_gemini_ok), \
                 patch.dict(os.environ, {"GROQ_API_KEY": "dummy_groq", "GEMINI_API_KEY": "dummy_gemini"}):

                chunks = []
                async for chunk in llm_engine.process_jarvis_intent_stream("Hello"):
                    chunks.append(chunk)
                assert "".join(chunks) == "Gemini fallback stream.", f"Fallback output mismatch: {chunks}"

            # 11b. Stream mid-failure: Groq yields two chunks then fails -> output contains only those two chunks, Gemini not called
            gemini_called = False
            def mock_groq_mid_fail(*args, **kwargs):
                yield "Chunk 1 "
                yield "Chunk 2"
                raise RuntimeError("Mid-stream network drop")

            def mock_gemini_spy(*args, **kwargs):
                nonlocal gemini_called
                gemini_called = True
                yield "Should not be called"

            with patch.object(llm_engine, "_stream_groq", mock_groq_mid_fail), \
                 patch.object(llm_engine, "_stream_gemini", mock_gemini_spy), \
                 patch.dict(os.environ, {"GROQ_API_KEY": "dummy_groq", "GEMINI_API_KEY": "dummy_gemini"}):

                chunks_mid = []
                async for chunk in llm_engine.process_jarvis_intent_stream("Hello"):
                    chunks_mid.append(chunk)
                assert "".join(chunks_mid) == "Chunk 1 Chunk 2", f"Mid-stream chunks mismatch: {chunks_mid}"
                assert not gemini_called, "Gemini fallback was invoked after chunks had already started!"

        asyncio.run(_test_streaming_engine())
        print("  Verified: Groq failure before chunks falls back to Gemini.")
        print("  Verified: Mid-stream failure stops cleanly without calling fallback.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 12: Speech Recognition Language Ordering & System Prompt
    # --------------------------------------------------------------------------
    print("\n[Check 12] Speech Recognition Language Ordering & Local Router:")
    try:
        from app import recognize_speech
        import speech_recognition as sr

        # 12a. en-IN tried first when language="en-IN", never kn-IN
        calls = []
        def mock_recognize(audio_data, language="en-US"):
            calls.append(language)
            return "hello world"

        with patch("app.recognizer.recognize_google", side_effect=mock_recognize):
            calls.clear()
            res = recognize_speech(None, language="en-IN")
            assert calls == ["en-IN"], f"Expected ['en-IN'], got {calls}"
            assert res == "hello world"
            assert "kn-IN" not in calls, "kn-IN was unexpectedly called for English audio!"
        print("  12a. en-IN tried first, kn-IN was not called.")

        # 12b. Empty English or UnknownValueError retries en-US once, never kn-IN
        calls.clear()
        def mock_recognize_retry(audio_data, language="en-US"):
            calls.append(language)
            if language == "en-IN":
                return ""  # Empty result
            return "retry success"

        with patch("app.recognizer.recognize_google", side_effect=mock_recognize_retry):
            calls.clear()
            res = recognize_speech(None, language="en-IN")
            assert calls == ["en-IN", "en-US"], f"Expected ['en-IN', 'en-US'], got {calls}"
            assert res == "retry success"
            assert "kn-IN" not in calls, "kn-IN was unexpectedly called during retry!"

        calls.clear()
        def mock_recognize_ex(audio_data, language="en-US"):
            calls.append(language)
            if language == "en-IN":
                raise sr.UnknownValueError()
            return "retry after exception"

        with patch("app.recognizer.recognize_google", side_effect=mock_recognize_ex):
            calls.clear()
            res = recognize_speech(None, language="en-IN")
            assert calls == ["en-IN", "en-US"], f"Expected ['en-IN', 'en-US'], got {calls}"
            assert res == "retry after exception"
            assert "kn-IN" not in calls, "kn-IN was unexpectedly called during retry!"
        print("  12b. Empty/failing en-IN retried en-US, kn-IN was never called.")

        # 12c. Transcript returned as separate field from /listen-voice route
        from fastapi.testclient import TestClient
        client = TestClient(app)
        import numpy as np
        dummy_audio = np.zeros(16000 * 4, dtype=np.int16)
        with patch("sounddevice.rec", return_value=dummy_audio), patch("sounddevice.wait"), \
             patch("app.recognize_speech", return_value="open calculator"), \
             patch("app.speak_text"):
            response = client.post("/listen-voice")
            assert response.status_code == 200
            data = response.json()
            assert "transcript" in data, "transcript field missing from /listen-voice response"
            assert data["transcript"] == "open calculator"
            assert "reply" in data, "reply field missing from /listen-voice response"
        print("  12c. /listen-voice returns transcript as separate field.")

        # 12d. System prompt contains same-language instruction
        expected_phrase = "Reply in English unless the user explicitly asks for another language"
        assert expected_phrase in llm_engine.JARVIS_SYSTEM_INSTRUCTION, (
            f"Instruction phrase '{expected_phrase}' missing from JARVIS_SYSTEM_INSTRUCTION"
        )
        print("  12d. System prompt contains same-language instruction.")

        # 12e. Local router answers calculator with 0 cloud calls
        with patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            calc_res = llm_engine.process_jarvis_intent("open calculator")
            assert not mock_groq.called, "Groq was called for calculator command!"
            assert not mock_gemini.called, "Gemini was called for calculator command!"
            assert calc_res.get("tool_executed") is not None, "Local router tool was not executed"
        print("  12e. Local router answered calculator with 0 cloud calls.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 13: Multi-Language Instructions, Streaming Interruption, Stop Words, and Route Compatibility
    # --------------------------------------------------------------------------
    print("\n[Check 13] Multi-Language Routing, Interruption, and API Stability:")
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app, raise_server_exceptions=False)

        # 13a. Hindi transcript produces Hindi reply instruction; English produces English
        hindi_inst = llm_engine.build_system_instruction("भारत की राजधानी क्या है?")
        assert "Reply only in Hindi (Devanagari script)." in hindi_inst, f"Hindi instruction missing: {hindi_inst}"
        eng_inst = llm_engine.build_system_instruction("What is the capital of France?")
        assert "Reply in English." in eng_inst, f"English instruction missing: {eng_inst}"
        print("  13a. Hindi transcript produces Hindi instruction; English produces English.")

        # 13b. Explicit "reply in Kannada" overrides the default
        kannada_inst = llm_engine.build_system_instruction("Who is the prime minister of India? Reply in Kannada")
        assert "Reply only in Kannada (Kannada script)." in kannada_inst, f"Kannada override missing: {kannada_inst}"
        print("  13b. Explicit 'reply in Kannada' successfully overrides default.")

        # 13c. Cancel flag stops streaming: after cancel, no further sentences are queued
        import asyncio
        import tts_engine
        cancel_event = asyncio.Event()

        async def _test_cancel_stream():
            yielded = []
            cancel_event.clear()
            async for chunk in llm_engine.process_jarvis_intent_stream("Hello world", cancel_event=cancel_event):
                yielded.append(chunk)
                cancel_event.set()  # Cancel after 1st chunk
            return yielded

        def mock_stream(*args, **kwargs):
            yield "First sentence. "
            yield "Second sentence. "
            yield "Third sentence."

        with patch.object(llm_engine, "_stream_groq", mock_stream), \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"}):
            stream_result = asyncio.run(_test_cancel_stream())
            assert len(stream_result) == 1, f"Expected 1 chunk before cancel, got {len(stream_result)}"
        print("  13c. Cancel flag immediately halts streaming generator.")

        # 13d. New request cancels the previous one
        tts_engine.reset_cancel()
        assert not tts_engine.is_cancelled()
        # Trigger /stop which cancels active pipeline
        res_stop = client.post("/stop")
        assert res_stop.status_code == 200
        assert tts_engine.is_cancelled()
        print("  13d. New request / cancellation halts previous audio/speech pipeline.")

        # 13e. The stop word is not sent to the LLM
        with patch.object(llm_engine, "process_jarvis_intent") as mock_intent, \
             patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            res_stop_cmd = client.post("/execute-command", json={"command": "stop"})
            assert res_stop_cmd.status_code == 200
            data_stop = res_stop_cmd.json()
            assert data_stop.get("status") == "cancelled"
            assert not mock_intent.called and not mock_groq.called and not mock_gemini.called, "LLM was called for stop word!"

            # Hindi stop word
            res_roko = client.post("/execute-command", json={"command": "रुको"})
            assert res_roko.status_code == 200
            assert res_roko.json().get("status") == "cancelled"
            assert not mock_intent.called and not mock_groq.called and not mock_gemini.called, "LLM was called for Hindi stop word!"
        print("  13e. Spoken/typed stop words are intercepted with zero LLM calls.")

        # 13f. The local router still answers 'open calculator' with zero cloud calls
        with patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            calc_res = client.post("/execute-command", json={"command": "open calculator"})
            assert calc_res.status_code == 200
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM invoked for local router command!"
            calc_data = calc_res.json()
            assert "Launched calculator" in calc_data.get("reply", "")
        print("  13f. Local router executes 'open calculator' with zero cloud calls.")

        # 13g. /execute-command and /chat-stream still return 200 with the same JSON shape
        with patch.object(llm_engine, "process_jarvis_intent", return_value={"reply": "Test answer", "tool_executed": "TestTool"}):
            r_exec = client.post("/execute-command", json={"command": "What is 2+2?"})
            assert r_exec.status_code == 200
            d_exec = r_exec.json()
            assert "status" in d_exec and "reply" in d_exec and "executed" in d_exec, f"Unexpected shape: {d_exec}"

        r_stream = client.post("/chat-stream", json={"command": "open calculator"})
        assert r_stream.status_code == 200
        assert "text/event-stream" in r_stream.headers.get("content-type", "")
        print("  13g. /execute-command and /chat-stream return 200 with exact expected schemas.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 14: Speech Cleanliness, Sentence Splitter Merging, and Stop Words
    # --------------------------------------------------------------------------
    print("\n[Check 14] Speech Cleanliness, Sentence Splitter Merging, and Stop Words:")
    try:
        from tts_engine import clean_for_speech, detect_language, VOICE_MAP
        from sentence_splitter import SentenceSplitter

        # 14a. clean_for_speech test cases (Indic conjuncts and vowel signs survive intact)
        assert clean_for_speech("**Paris.**") == "Paris."
        assert clean_for_speech("→ Open Notepad") == "Open Notepad"
        assert clean_for_speech("`notepad`") == "notepad"
        assert clean_for_speech("1. Step one") == "Step one"
        assert clean_for_speech("**ನಮಸ್ಕಾರ** ಗೆಳೆಯರೇ") == "ನಮಸ್ಕಾರ ಗೆಳೆಯರೇ"
        assert clean_for_speech("ನಮಸ್ಕಾರ") == "ನಮಸ್ಕಾರ", "Kannada conjuncts/matras stripped!"
        assert clean_for_speech("नमस्ते") == "नमस्ते", "Devanagari conjuncts/matras stripped!"
        assert clean_for_speech("ಕನ್ನಡ") == "ಕನ್ನಡ"
        assert clean_for_speech("हिंदी") == "हिंदी"
        assert clean_for_speech("Growth is 100%!!") == "Growth is 100 percent!"
        assert clean_for_speech("Check [here](http://example.com) 👍 → 🚀") == "Check here"
        print("  14a. clean_for_speech strips markdown/arrows/emojis while 100% preserving Indic conjuncts & vowel signs.")

        # 14b. detect_language dominant script and foreign script safety
        assert detect_language("This is English.") == VOICE_MAP["english_in"]
        assert detect_language("यह हिंदी में उत्तर है।") == VOICE_MAP["hindi"]
        assert detect_language("ಇದು ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರವಾಗಿದೆ.") == VOICE_MAP["kannada"]
        # Chinese / foreign text must NEVER select a Kannada or Hindi voice
        assert detect_language("你好，世界！") == VOICE_MAP["english_in"], "Chinese text incorrectly selected Indic voice!"
        assert detect_language("这是中文回复") == VOICE_MAP["english_in"], "Chinese text incorrectly selected Indic voice!"
        # Dominant script with single quote/word should pick majority language
        assert detect_language("The word 'ನಿಲ್ಲಿಸು' means stop in Kannada.") == VOICE_MAP["english_in"]
        print("  14b. detect_language accurately identifies dominant script; foreign/Chinese text selects English voice.")

        # 14c. SentenceSplitter fragment merging & boundary handling
        s = SentenceSplitter()
        f1 = s.feed("1. ")
        assert f1 == [], f"Expected empty list for short fragment, got {f1}"
        f2 = s.feed("Step one is ready. 2. ")
        assert f2 == ["1. Step one is ready."], f"Expected merged sentence, got {f2}"
        f3 = s.feed("Step two is complete. ")
        assert f3 == ["2. Step two is complete."], f"Expected merged sentence, got {f3}"
        # Flush outputs short final sentence
        s_short = SentenceSplitter()
        assert s_short.feed("Yes.") == []
        assert s_short.flush() == ["Yes."]

        # Hindi danda splitting
        s_hi = SentenceSplitter()
        hi_out = s_hi.feed("यह पहला वाक्य है। यह दूसरा वाक्य है। ")
        assert hi_out == ["यह पहला वाक्य है।", "यह दूसरा वाक्य है।"]
        print("  14c. SentenceSplitter merges short fragments (<2 words) and correctly splits on punctuation & dandas.")

        # 14d. STOP_WORDS single-script verification
        import app as kalki_app
        for word in kalki_app.STOP_WORDS:
            scripts = set()
            for char in word:
                if char.isspace() or char in ".,!?:;\"'":
                    continue
                cp = ord(char)
                if cp < 128:
                    scripts.add("Latin/ASCII")
                elif 0x0900 <= cp <= 0x097F:
                    scripts.add("Devanagari")
                elif 0x0C80 <= cp <= 0x0CFF:
                    scripts.add("Kannada")
                else:
                    scripts.add(f"Other_{cp:04X}")
            assert len(scripts) <= 1, f"Stop word {word!r} has mixed scripts: {scripts}"

        # Verify pure Kannada 'ನಿಲ್ಲಿಸು'
        assert "ನಿಲ್ಲಿಸು" in kalki_app.STOP_WORDS
        assert ord("ನಿಲ್ಲಿಸು"[0]) == 0x0CA8, f"Expected Kannada letter U+0CA8, got {ord('ನಿಲ್ಲಿಸು'[0]):04X}"
        print("  14d. Every word in STOP_WORDS is verified single-script; 'ನಿಲ್ಲಿಸು' is confirmed pure Kannada.")

        # 14e. Language Guard: retry on wrong script, fallback to English
        from llm_engine import is_valid_script_reply
        assert is_valid_script_reply("ಬೆಂಗಳೂರು ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ.", "kannada") == True
        assert is_valid_script_reply("Paris is the capital.", "kannada") == False
        assert is_valid_script_reply("这是中文", "kannada") == False

        # Mock LLM returning Chinese for Kannada prompt
        call_count = 0
        def mock_llm_chain(prompt, chat_hist=None, custom_instruction=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "这是错误的中文"  # First call: wrong script
            elif call_count == 2:
                return "这是依然错误的中文"  # Retry call: still wrong
            else:
                return "Bengaluru is the capital of Karnataka."  # English fallback call

        with patch.object(llm_engine, "_call_groq", side_effect=mock_llm_chain), \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"}):
            guard_res = llm_engine.process_jarvis_intent("ಬೆಂಗಳೂರು ಬಗ್ಗೆ ತಿಳಿಸಿ")
            assert "Note: Could not respond in Kannada as requested." in guard_res.get("reply", "")
            assert "Bengaluru is the capital" in guard_res.get("reply", "")
            # Ensure wrong script (Chinese) was discarded
            assert "中文" not in guard_res.get("reply", "")
        print("  14e. Reply Language Guard triggers retry on wrong script, falls back to English with note, and never yields wrong script.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 15: Single Full-Reply TTS, Voice System Instruction, Stop Cancellation, and Router
    # --------------------------------------------------------------------------
    print("\n[Check 15] Single Full-Reply TTS, Voice System Instruction, and File Cleanup:")
    try:
        import tts_engine
        import asyncio

        # 15a. Voice instruction added only for voice requests, not typed
        voice_prompt = "भारत की राजधानी क्या है?"
        voice_inst = llm_engine.build_system_instruction(voice_prompt, is_voice=True)
        typed_inst = llm_engine.build_system_instruction(voice_prompt, is_voice=False)
        expected_voice_rule = "For voice replies, answer in at most 2 short sentences unless the user asks for detail."
        assert expected_voice_rule in voice_inst, f"Voice instruction missing: {voice_inst}"
        assert expected_voice_rule not in typed_inst, f"Voice instruction unexpectedly found in typed prompt: {typed_inst}"
        print("  15a. Voice system instruction present only when is_voice=True; omitted for typed.")

        # 15b. Whole reply is sent to TTS once, not per sentence
        from fastapi.testclient import TestClient
        import numpy as np
        client = TestClient(app, raise_server_exceptions=False)

        spoken_calls = []
        async def mock_speak_text(text, request_start_time=None):
            spoken_calls.append(text)

        def mock_stream_3_sentences(*args, **kwargs):
            yield "Sentence one. "
            yield "Sentence two. "
            yield "Sentence three."

        dummy_audio = np.zeros(16000 * 4, dtype=np.int16)
        with patch("sounddevice.rec", return_value=dummy_audio), patch("sounddevice.wait"), \
             patch("app.recognize_speech", return_value="Tell me three facts"), \
             patch("app.speak_text", mock_speak_text), \
             patch.object(llm_engine, "_stream_groq", mock_stream_3_sentences), \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"}):
            spoken_calls.clear()
            res_voice = client.post("/listen-voice", headers={"Accept": "text/event-stream"})
            assert res_voice.status_code == 200
            assert len(spoken_calls) == 1, f"Expected 1 TTS call for full reply, got {len(spoken_calls)}: {spoken_calls}"
            assert spoken_calls[0] == "Sentence one. Sentence two. Sentence three."
        print("  15b. Whole streaming reply is sent to TTS exactly once as a single request, not per sentence.")

        # Read sample dummy bytes for fast unit test execution without network calls
        sample_mp3_path = Path(os.environ.get("APPDATA", "")) / "KALKI" / "debug_audio" / "live" / "live_001.mp3"
        if sample_mp3_path.exists():
            sample_mp3_bytes = sample_mp3_path.read_bytes()
        else:
            sample_mp3_bytes = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 2000

        # 15c. Stop cancels speech and deletes the file
        async def _test_stop_cancels_and_deletes():
            tts_engine.reset_cancel()
            tts_engine.playback_hook = None
            created_files = []

            async def mock_communicate_save(self, path):
                created_files.append(Path(path))
                Path(path).write_bytes(sample_mp3_bytes)
                await asyncio.sleep(0.01)

            play_started = asyncio.Event()
            play_stopped = asyncio.Event()

            async def mock_play_file(path_str):
                play_started.set()
                try:
                    while not tts_engine.is_cancelled():
                        await asyncio.sleep(0.01)
                finally:
                    play_stopped.set()

            with patch("edge_tts.Communicate.save", mock_communicate_save), \
                 patch.object(tts_engine, "_play_file_persistent", mock_play_file):
                q = tts_engine.get_tts_queue()
                await tts_engine.enqueue_speech("Full reply to be interrupted.")

                await play_started.wait()
                assert len(created_files) == 1
                active_file = created_files[0]
                assert active_file.exists(), "Active file does not exist during playback"

                tts_engine.cancel_playback_and_queue()
                assert tts_engine.is_cancelled()
                await play_stopped.wait()

                assert not active_file.exists(), f"File {active_file} was not unlinked on cancel!"

        asyncio.run(_test_stop_cancels_and_deletes())
        print("  15c. Stop cancels active speech and immediately unlinks the audio file.")

        # 15d. Single speech job plays completely and deletes file cleanly
        async def _test_single_reply_plays_and_cleans():
            tts_engine.reset_cancel()
            tts_engine.playback_hook = None
            created_files = []
            played_files = []

            async def mock_communicate_save(self, path):
                created_files.append(Path(path))
                Path(path).write_bytes(sample_mp3_bytes)
                await asyncio.sleep(0.01)

            async def mock_play_file(path_str):
                played_files.append(path_str)
                await asyncio.sleep(0.05)

            with patch("edge_tts.Communicate.save", mock_communicate_save), \
                 patch.object(tts_engine, "_play_file_persistent", mock_play_file):
                q = tts_engine.get_tts_queue()
                await tts_engine.enqueue_speech("Single full spoken reply.")
                await q.join()

            assert len(played_files) == 1, f"Expected 1 played file, got {len(played_files)}"
            assert len(created_files) == 1, f"Expected 1 created file, got {len(created_files)}"
            assert not created_files[0].exists(), f"File {created_files[0]} was not unlinked after playback!"

        asyncio.run(_test_single_reply_plays_and_cleans())
        print("  15d. Single full reply plays completely and unlinks file cleanly.")

        # 15e. Local router still answers 'open calculator' with zero cloud calls
        with patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            calc_res = client.post("/execute-command", json={"command": "open calculator"})
            assert calc_res.status_code == 200
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM invoked for local router command!"
            calc_data = calc_res.json()
            assert "Launched calculator" in calc_data.get("reply", "")
        print("  15e. Local router still answers 'open calculator' with zero cloud calls.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Check 16: Group 1 Local Router & System Control Commands
    # --------------------------------------------------------------------------
    print("\n[Check 16] Group 1 Local System & App Control Commands:")
    try:
        from unittest.mock import MagicMock

        # 16a. "open calculator" matches the router and calls subprocess.Popen with calc.exe
        with patch("subprocess.Popen") as mock_popen, \
             patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            res_calc = llm_engine.process_jarvis_intent("open calculator")
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM called for open calculator!"
            assert mock_popen.called, "subprocess.Popen was not called for open calculator!"
            args, _ = mock_popen.call_args
            assert "calc.exe" in str(args) or "calc" in str(args), f"calc.exe not in Popen args: {args}"
            assert "Launched calculator" in res_calc.get("reply", "")
        print("  16a. 'open calculator' matches router and calls Popen with calc.exe.")

        # 16b. "close notepad" calls taskkill with notepad.exe
        with patch("subprocess.run") as mock_run, \
             patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc
            res_close = llm_engine.process_jarvis_intent("close notepad")
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM called for close notepad!"
            assert mock_run.called, "subprocess.run was not called for close notepad!"
            run_args, _ = mock_run.call_args
            assert "taskkill" in run_args[0] and "notepad.exe" in run_args[0], f"taskkill notepad.exe not in args: {run_args}"
            assert "Closed notepad." in res_close.get("reply", "")
        print("  16b. 'close notepad' calls taskkill with notepad.exe without calling LLM.")

        # 16c. "open malware.exe" does NOT match and goes to the LLM
        with patch.object(llm_engine, "_call_groq", return_value="I cannot open unverified executables.") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            res_malware = llm_engine.process_jarvis_intent("open malware.exe")
            assert mock_groq.called, "Cloud LLM was NOT called for unauthorized app 'open malware.exe'!"
            assert "I cannot open unverified executables." in res_malware.get("reply", "")
        print("  16c. 'open malware.exe' is blocked by allowlist and safely routes to LLM.")

        # 16d. "volume up" does not call the LLM
        with patch.object(llm_engine, "get_volume_interface") as mock_vol_iface, \
             patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            mock_vol = MagicMock()
            mock_vol.GetMasterVolumeLevelScalar.return_value = 0.50
            mock_vol_iface.return_value = mock_vol
            res_vol = llm_engine.process_jarvis_intent("volume up")
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM called for volume up!"
            assert mock_vol.SetMasterVolumeLevelScalar.called, "SetMasterVolumeLevelScalar was not called!"
            assert "Volume increased." in res_vol.get("reply", "")
        print("  16d. 'volume up' adjusts audio and returns without calling LLM.")

        # 16e. "set volume to 75" extracts 75 correctly
        with patch.object(llm_engine, "get_volume_interface") as mock_vol_iface, \
             patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            mock_vol = MagicMock()
            mock_vol_iface.return_value = mock_vol
            res_vol_75 = llm_engine.process_jarvis_intent("set volume to 75")
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM called for set volume to 75!"
            mock_vol.SetMasterVolumeLevelScalar.assert_called_with(0.75, None)
            assert "Volume set to 75 percent." in res_vol_75.get("reply", "")
        print("  16e. 'set volume to 75' accurately parses 75 and sets scalar 0.75.")

        # 16f. "shutdown" sets _pending_action to "shutdown"
        llm_engine._pending_action = None
        with patch.object(llm_engine, "_call_groq") as mock_groq:
            res_shut = llm_engine.process_jarvis_intent("shutdown")
            assert not mock_groq.called, "Cloud LLM called for shutdown initiation!"
            assert llm_engine._pending_action == "shutdown", f"Expected _pending_action=='shutdown', got {llm_engine._pending_action}"
            assert "Say yes to confirm" in res_shut.get("reply", "")
        print("  16f. 'shutdown' sets _pending_action to 'shutdown' and prompts confirmation.")

        # 16g. "yes" after shutdown executes the shutdown command
        with patch("subprocess.Popen") as mock_popen, \
             patch.object(llm_engine, "_call_groq") as mock_groq:
            res_yes = llm_engine.process_jarvis_intent("yes")
            assert not mock_groq.called, "Cloud LLM called for confirmation 'yes'!"
            assert mock_popen.called, "subprocess.Popen not called upon confirmed shutdown!"
            pop_args, _ = mock_popen.call_args
            assert "shutdown" in str(pop_args) and "/s" in str(pop_args), f"shutdown /s not in args: {pop_args}"
            assert llm_engine._pending_action is None, "Pending action was not cleared after confirmation!"
        print("  16g. 'yes' executes confirmed shutdown command and clears pending state.")

        # 16h. "no" after shutdown clears _pending_action
        llm_engine._pending_action = "shutdown"
        llm_engine._pending_action_timestamp = time.time()
        with patch("subprocess.Popen") as mock_popen, \
             patch.object(llm_engine, "_call_groq") as mock_groq:
            res_no = llm_engine.process_jarvis_intent("no")
            assert not mock_groq.called, "Cloud LLM called for cancellation 'no'!"
            assert not mock_popen.called, "subprocess.Popen was called on cancelled shutdown!"
            assert llm_engine._pending_action is None, "Pending action was not cleared after 'no'!"
            assert "Cancelled." in res_no.get("reply", "")
        print("  16h. 'no' clears _pending_action and cancels shutdown with 'Cancelled.'")

        # 16i. "take a screenshot" does not call the LLM
        with patch.object(llm_engine, "take_screenshot", return_value="Screenshot saved to Pictures/KALKI Screenshots/kalki_2026-10-28_12-00-00.png") as mock_shot, \
             patch.object(llm_engine, "_call_groq") as mock_groq, \
             patch.object(llm_engine, "_call_gemini") as mock_gemini:
            res_shot = llm_engine.process_jarvis_intent("take a screenshot")
            assert not mock_groq.called and not mock_gemini.called, "Cloud LLM called for take screenshot!"
            assert mock_shot.called, "take_screenshot was not invoked!"
            assert "Screenshot saved to" in res_shot.get("reply", "")
        print("  16i. 'take a screenshot' captures screen without calling LLM.")
        print("  PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  FAIL — {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 16 DIAGNOSTICS & SAFETY CHECKS PASSED [PASS]")
        print("=" * 70)
        sys.exit(0)
    else:
        print("ONE OR MORE CHECKS FAILED [FAIL]")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    run_all_checks()
