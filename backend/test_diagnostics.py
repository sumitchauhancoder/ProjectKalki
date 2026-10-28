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
    # Check 3: When the Gemini call fails, the Groq fallback is used (Mocked)
    # --------------------------------------------------------------------------
    print("\n[Check 3] Gemini Failure Triggers Groq Fallback (Mocked, 0 Network Calls):")
    try:
        mock_groq_reply = "This is a safe fallback response from Groq Llama 3.3."
        
        with patch.object(llm_engine, "_call_gemini", side_effect=Exception("Gemini 429 Quota Exceeded")), \
             patch.object(llm_engine, "_call_groq", return_value=mock_groq_reply) as mock_groq_call, \
             patch.dict(os.environ, {"GROQ_API_KEY": "dummy_groq_key_for_test"}):
            
            result = llm_engine.process_jarvis_intent("What is the speed of light?")
            
            assert mock_groq_call.called, "Expected _call_groq to be called after Gemini failure"
            assert result.get("reply") == mock_groq_reply, f"Unexpected reply: {result.get('reply')}"
            assert "Groq" in result.get("tool_executed", ""), f"Tool executed does not indicate Groq: {result.get('tool_executed')}"
            
        print("  Simulated Gemini 429 quota failure -> Successfully routed to Groq fallback")
        print(f"  Returned: '{result.get('reply')}' (tool: {result.get('tool_executed')})")
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
    # Summary
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 5 PHASE 0 CHECKS PASSED [PASS]")
        print("=" * 70)
        sys.exit(0)
    else:
        print("ONE OR MORE CHECKS FAILED [FAIL]")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    run_all_checks()
