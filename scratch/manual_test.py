import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

commands = [
    "open calculator",
    "volume up",
    "take a screenshot",
    "shutdown",
    "no"
]

print("=== MANUAL ENDPOINT TEST EXECUTION ===")
for cmd in commands:
    res = client.post("/execute-command", json={"command": cmd})
    data = res.json()
    print(f"COMMAND: \"{cmd}\"")
    print(f"STATUS:  {res.status_code}")
    print(f"REPLY:   \"{data.get('reply')}\"")
    print(f"TOOL:    \"{data.get('tool_executed')}\"")
    print("-" * 40)
