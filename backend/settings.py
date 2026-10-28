import os
import json
from pathlib import Path

def get_settings_path() -> Path:
    """Returns path to settings.json in %APPDATA%/KALKI/ or backend/ fallback."""
    app_data = os.getenv("APPDATA")
    if app_data:
        kalki_dir = Path(app_data) / "KALKI"
        try:
            kalki_dir.mkdir(parents=True, exist_ok=True)
            return kalki_dir / "settings.json"
        except Exception:
            pass
    return Path(__file__).resolve().parent / "settings.json"

def load_settings() -> dict:
    """Loads user settings from settings.json; defaults language to 'en-IN'."""
    path = get_settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"[Settings Warning]: Failed to read settings: {type(e).__name__}")
    return {"language": "en-IN"}

def save_settings(new_data: dict) -> dict:
    """Merges and saves user settings to settings.json."""
    path = get_settings_path()
    current = load_settings()
    current.update(new_data)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except Exception as e:
        print(f"[Settings Warning]: Failed to save settings: {type(e).__name__}")
    return current
