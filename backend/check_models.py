import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Explicitly load backend/.env
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

import llm_engine

def check_configured_models() -> dict:
    """
    Queries Google Gemini and Groq model APIs to list available models
    and verify whether configured model names exist.
    Outputs model names ONLY — NEVER outputs keys or secrets.
    """
    configured_gemini = os.getenv("GEMINI_MODEL", "").strip() or llm_engine.DEFAULT_GEMINI_MODEL
    configured_groq = os.getenv("GROQ_MODEL", "").strip() or llm_engine.DEFAULT_GROQ_MODEL

    results = {
        "gemini": {"configured": configured_gemini, "found": False, "models": []},
        "groq": {"configured": configured_groq, "found": False, "models": []}
    }

    print("=" * 70)
    print("PROJECT KALKI — MODEL AVAILABILITY CHECK")
    print("=" * 70)

    # 1. Check Gemini
    print(f"\n[Gemini Check] Configured Model: '{configured_gemini}'")
    g_client = llm_engine.get_gemini_client()
    if not g_client:
        print("  Status: Gemini client unavailable (GEMINI_API_KEY unset).")
    else:
        try:
            gemini_pager = g_client.models.list()
            # Normalize names (both with and without 'models/' prefix)
            raw_names = [m.name for m in gemini_pager]
            clean_names = [name.replace("models/", "") for name in raw_names]
            results["gemini"]["models"] = clean_names

            # Check if configured model exists
            is_found = (
                configured_gemini in clean_names or
                configured_gemini in raw_names or
                f"models/{configured_gemini}" in raw_names
            )
            results["gemini"]["found"] = is_found

            print(f"  Available Gemini Models ({len(clean_names)} total):")
            # Print sample / popular models for clear visibility
            relevant_models = [m for m in clean_names if "gemini" in m.lower()]
            for name in relevant_models[:12]:
                print(f"    - {name}")
            if len(relevant_models) > 12:
                print(f"    ... and {len(relevant_models) - 12} more")

            if is_found:
                print(f"  Result: [FOUND] Configured model '{configured_gemini}' is available.")
            else:
                print(f"  Result: [NOT FOUND] Configured model '{configured_gemini}' was not listed.")
        except Exception as e:
            status = getattr(e, "status_code", getattr(e, "code", None))
            status_str = f" status={status}" if status else ""
            print(f"  Status: Failed to query Gemini models ({type(e).__name__}{status_str})")

    # 2. Check Groq
    print(f"\n[Groq Check] Configured Model: '{configured_groq}'")
    gr_client = llm_engine.get_groq_client()
    if not gr_client:
        print("  Status: Groq client unavailable (GROQ_API_KEY unset).")
    else:
        try:
            gr_models_data = gr_client.models.list()
            groq_ids = [m.id for m in gr_models_data.data]
            results["groq"]["models"] = groq_ids

            is_found = configured_groq in groq_ids
            results["groq"]["found"] = is_found

            print(f"  Available Groq Models ({len(groq_ids)} total):")
            for m_id in groq_ids:
                print(f"    - {m_id}")

            if is_found:
                print(f"  Result: [FOUND] Configured model '{configured_groq}' is available.")
            else:
                print(f"  Result: [NOT FOUND] Configured model '{configured_groq}' was not listed.")
        except Exception as e:
            status = getattr(e, "status_code", getattr(e, "code", None))
            status_str = f" status={status}" if status else ""
            print(f"  Status: Failed to query Groq models ({type(e).__name__}{status_str})")

    print("\n" + "=" * 70)
    return results

if __name__ == "__main__":
    check_configured_models()
