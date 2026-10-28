from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import bcrypt
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import User
import uuid

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

def hash_password(password: str) -> str:
    """Hash password using standard bcrypt with 72-byte safe limit."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(plain_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False

class RegisterSchema(BaseModel):
    name: str
    username: str
    email: str
    password: str

class LoginSchema(BaseModel):
    identifier: str  # Accepts either username or email
    password: str

class ForgotPasswordSchema(BaseModel):
    email: str

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterSchema, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

    clean_name = payload.name.strip()
    clean_username = payload.username.strip()
    clean_email = payload.email.strip()
    password = payload.password

    # 400 for invalid/empty input
    if not clean_name or not clean_username or not clean_email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, username, email, and password cannot be empty."
        )

    try:
        existing_user = db.query(User).filter(
            (User.email == clean_email) | (User.username == clean_username)
        ).first()
        
        # 409 Conflict for duplicate username or email
        if existing_user:
            if existing_user.username.lower() == clean_username.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username is already registered."
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered."
            )
        
        hashed_pwd = hash_password(password)
        new_user = User(
            name=clean_name,
            username=clean_username,
            email=clean_email,
            hashed_password=hashed_pwd
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "Registration successful", 
            "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Auth Error]: Registration failure: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@auth_router.post("/login", status_code=status.HTTP_200_OK)
def login_user(payload: LoginSchema, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

    clean_id = payload.identifier.strip()
    password = payload.password

    # 400 for invalid/empty input
    if not clean_id or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier and password cannot be empty."
        )

    try:
        user = db.query(User).filter(
            (User.username == clean_id) | (User.email == clean_id)
        ).first()
        
        # 401 Unauthorized for invalid user or wrong password
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Check your username/email and password."
            )
        
        return {
            "message": "Login successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "email": user.email
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Auth Error]: Login failure: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@auth_router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(payload: ForgotPasswordSchema, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

    clean_email = payload.email.strip()
    if not clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email cannot be empty."
        )

    try:
        user = db.query(User).filter(User.email == clean_email).first()
        if not user:
            return {"message": "If that email exists, password reset instructions have been sent."}
        
        token = str(uuid.uuid4())
        user.reset_token = token
        db.commit()
        
        return {
            "message": "Password reset token generated.", 
            "dev_reset_token": token
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Auth Error]: Forgot-password failure: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")
