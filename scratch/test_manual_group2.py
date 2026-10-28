import sys
from pathlib import Path
from unittest.mock import patch

# Add repository root and backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

commands = [
    "type Hello from KALKI",
    "copy",
    "find file requirements.txt",
    "scroll down",
    "press f5"
]

print("=" * 60)
print("TESTING GROUP 2 MANUAL COMMANDS VIA /execute-command")
print("=" * 60)

with patch("pyautogui.typewrite") as mock_type, \
     patch("pyautogui.write") as mock_write, \
     patch("pyautogui.hotkey") as mock_hotkey, \
     patch("pyautogui.press") as mock_press, \
     patch("pyautogui.scroll") as mock_scroll:

    for cmd in commands:
        resp = client.post("/execute-command", json={"command": cmd})
        status = resp.status_code
        data = resp.json()
        print(f"Command: '{cmd}'")
        print(f"Status:  {status}")
        print(f"Reply:   '{data.get('reply')}'")
        print(f"Tool:    '{data.get('tool_executed')}'")
        print("-" * 60)
