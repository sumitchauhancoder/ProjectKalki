import sys
import getpass
from pathlib import Path

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import User
from auth import hash_password

def promote_or_create_admin():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("PROJECT KALKI — ADMINISTRATOR ACCOUNT SETUP")
        print("=" * 60)
        
        username = input("Enter username to promote to administrator: ").strip()
        if not username:
            print("Error: Username cannot be empty.")
            sys.exit(1)

        user = db.query(User).filter(User.username == username).first()
        if user:
            print(f"Found existing user: '{user.username}' ({user.email})")
            confirm_pwd = getpass.getpass("Enter current password to confirm promotion: ")
            from auth import verify_password
            if not verify_password(confirm_pwd, user.hashed_password):
                print("Error: Invalid password. Promotion aborted.")
                sys.exit(1)
            
            user.role = "admin"
            user.status = "active"
            db.commit()
            print(f"[SUCCESS] User '{username}' promoted to administrator successfully.")
        else:
            print(f"User '{username}' does not exist. Creating new administrator account.")
            name = input("Enter Full Name: ").strip()
            email = input("Enter Email Address: ").strip().lower()
            password = getpass.getpass("Enter Password: ")
            confirm_pwd = getpass.getpass("Confirm Password: ")
            
            if password != confirm_pwd:
                print("Error: Passwords do not match.")
                sys.exit(1)
            if not name or not email or not password:
                print("Error: All fields are required.")
                sys.exit(1)
                
            hashed = hash_password(password)
            new_admin = User(
                name=name,
                username=username,
                email=email,
                hashed_password=hashed,
                role="admin",
                status="active"
            )
            db.add(new_admin)
            db.commit()
            print(f"[SUCCESS] New administrator account '{username}' created successfully.")
            
    except Exception as e:
        print(f"Error during admin creation: {type(e).__name__}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    promote_or_create_admin()
