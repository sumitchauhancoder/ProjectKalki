import sys
from pathlib import Path

# Ensure backend directory is in path
backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app import app
from database import SessionLocal
from models import User

client = TestClient(app)

def run_verification():
    print("=" * 60)
    print("TASK 3 VERIFICATION: REGISTER & DUAL LOGIN COMPATIBILITY")
    print("=" * 60)

    # 1. Register test user "testlogin" (or clean up first if exists)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "testlogin").first()
        if existing:
            db.delete(existing)
            db.commit()
            print("Existing test user removed for clean test.")
    finally:
        db.close()

    print("\n[Step 1] Register test user 'testlogin':")
    reg_payload = {
        "name": "Test Login User",
        "username": "testlogin",
        "email": "testlogin@kalki.ai",
        "password": "Test1234"
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    print(f"  Register Status Code: {reg_resp.status_code}")
    assert reg_resp.status_code == 201, f"Expected 201 Created, got {reg_resp.status_code}: {reg_resp.text}"
    reg_data = reg_resp.json()
    print("  Register Response:", reg_data.get("message"))

    # 2. Test login with {"identifier":"testlogin","password":"Test1234"}
    print("\n[Step 2] Login with 'identifier':")
    id_payload = {
        "identifier": "testlogin",
        "password": "Test1234"
    }
    id_resp = client.post("/api/auth/login", json=id_payload)
    print(f"  Login Status Code: {id_resp.status_code}")
    assert id_resp.status_code == 200, f"Expected 200 OK, got {id_resp.status_code}: {id_resp.text}"
    id_data = id_resp.json()
    token_1 = id_data.get("token") or id_data.get("access_token")
    assert token_1 is not None, "Token missing in response!"
    parts_1 = token_1.split(".")
    assert len(parts_1) == 3, f"Token is not a valid 3-part JWT string: {len(parts_1)} parts"
    print("  Token received (3-part JWT confirmed: header.payload.signature)")

    # 3. Test login with {"username":"testlogin","password":"Test1234"}
    print("\n[Step 3] Login with 'username' (backward-compatible alias):")
    user_payload = {
        "username": "testlogin",
        "password": "Test1234"
    }
    user_resp = client.post("/api/auth/login", json=user_payload)
    print(f"  Login Status Code: {user_resp.status_code}")
    assert user_resp.status_code == 200, f"Expected 200 OK, got {user_resp.status_code}: {user_resp.text}"
    user_data = user_resp.json()
    token_2 = user_data.get("token") or user_data.get("access_token")
    assert token_2 is not None, "Token missing in response!"
    parts_2 = token_2.split(".")
    assert len(parts_2) == 3, f"Token is not a valid 3-part JWT string: {len(parts_2)} parts"
    print("  Token received (3-part JWT confirmed: header.payload.signature)")

    # 4. Confirm JWT structure validation
    print("\n[Step 4] Confirm JWT token validity:")
    print(f"  Identifier login token parts: {len(parts_1)} parts")
    print(f"  Username alias login token parts: {len(parts_2)} parts")
    print("  All JWT validation checks passed.")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED [SUCCESS]")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
