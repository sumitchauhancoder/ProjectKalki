import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator
from database import get_db
from models import User

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

# --------------------------------------------------------------------------
# JWT Secret Management
# --------------------------------------------------------------------------
def get_jwt_secret() -> str:
    """Reads JWT secret from environment or loads/generates persistent key in %APPDATA%/KALKI/secret.key."""
    env_secret = os.getenv("JWT_SECRET")
    if env_secret and env_secret.strip():
        return env_secret.strip()

    appdata = os.getenv("APPDATA")
    if appdata:
        secret_file = Path(appdata) / "KALKI" / "secret.key"
    else:
        secret_file = Path(__file__).resolve().parent / "secret.key"

    try:
        if secret_file.exists():
            content = secret_file.read_text(encoding="utf-8").strip()
            if content:
                return content
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        new_secret = secrets.token_hex(32)
        secret_file.write_text(new_secret, encoding="utf-8")
        return new_secret
    except Exception:
        # Fallback to deterministic process-lifetime fallback if disk write is restricted
        return "kalki-local-jwt-secret-fallback-key-32bytes"

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

def create_access_token(user: User) -> str:
    """Creates a signed 24-hour JWT token for the user."""
    secret = get_jwt_secret()
    now = datetime.utcnow()
    payload = {
        "sub": str(user.id),
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "role": getattr(user, "role", "user") or "user",
        "status": getattr(user, "status", "active") or "active",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRATION_HOURS)).timestamp())
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )

# --------------------------------------------------------------------------
# Password Hashing
# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
# FastApi Dependencies
# --------------------------------------------------------------------------
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Optional[Session] = Depends(get_db)
) -> User:
    """Dependency that extracts user from Authorization header (Bearer token)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required."
        )
    token = authorization.split(" ")[1].strip()
    payload = decode_access_token(token)
    user_id = payload.get("id") or payload.get("sub")

    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )
    if getattr(user, "status", "active") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled."
        )
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the authenticated user is an administrator."""
    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required."
        )
    return current_user

# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class RegisterSchema(BaseModel):
    name: str
    username: str
    email: str
    password: str

class LoginSchema(BaseModel):
    identifier: Optional[str] = None  # Primary field: accepts either username or email
    username: Optional[str] = None    # Backward-compatible alias for identifier
    password: str

    @model_validator(mode="before")
    @classmethod
    def resolve_identifier(cls, data):
        if isinstance(data, dict):
            # If the request has "username" and no "identifier", use "username" as the identifier value
            ident = data.get("identifier") or data.get("username")
            if ident:
                data["identifier"] = ident
                if not data.get("username"):
                    data["username"] = ident
        return data

class ForgotPasswordSchema(BaseModel):
    email: str

# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterSchema, db: Optional[Session] = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

    clean_name = payload.name.strip()
    clean_username = payload.username.strip()
    clean_email = payload.email.strip().lower()
    password = payload.password

    if not clean_name or not clean_username or not clean_email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, username, email, and password cannot be empty."
        )

    try:
        existing_user = db.query(User).filter(
            (User.email == clean_email) | (User.username == clean_username)
        ).first()

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
            hashed_password=hashed_pwd,
            role="user",
            status="active"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        token = create_access_token(new_user)

        return {
            "message": "Registration successful",
            "token": token,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role,
                "status": new_user.status
            }
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

    ident = payload.identifier or payload.username or ""
    clean_id = ident.strip()
    password = payload.password

    if not clean_id or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier and password cannot be empty."
        )

    try:
        user = db.query(User).filter(
            (User.username == clean_id) | (User.email == clean_id.lower())
        ).first()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Check your username/email and password."
            )

        if getattr(user, "status", "active") == "disabled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been disabled. Please contact an administrator."
            )

        user.last_login = datetime.utcnow()
        db.commit()

        token = create_access_token(user)

        return {
            "message": "Login successful",
            "token": token,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "email": user.email,
                "role": getattr(user, "role", "user") or "user",
                "status": getattr(user, "status", "active") or "active"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Auth Error]: Login failure: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Database is currently unavailable.")

@auth_router.get("/me", status_code=status.HTTP_200_OK)
def get_authenticated_user(current_user: User = Depends(get_current_user)):
    """Verifies token and returns authenticated user object."""
    user_data = {
        "id": current_user.id,
        "name": current_user.name,
        "username": current_user.username,
        "email": current_user.email,
        "role": getattr(current_user, "role", "user") or "user",
        "status": getattr(current_user, "status", "active") or "active",
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }
    return {
        "user": user_data,
        **user_data
    }
