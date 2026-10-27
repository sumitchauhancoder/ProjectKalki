from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from database import get_db
from models import User
import uuid

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

@auth_router.post("/register")
def register_user(payload: RegisterSchema, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.username)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or Email is already registered.")
    
    hashed_pwd = pwd_context.hash(payload.password)
    new_user = User(
        name=payload.name,
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "Registration successful", 
        "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}
    }

@auth_router.post("/login")
def login_user(payload: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == payload.identifier) | (User.email == payload.identifier)
    ).first()
    
    if not user or not pwd_context.verify(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials. Check your username/email and password.")
    
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "email": user.email
        }
    }

@auth_router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return {"message": "If that email exists, password reset instructions have been sent."}
    
    token = str(uuid.uuid4())
    user.reset_token = token
    db.commit()
    
    return {
        "message": "Password reset token generated.", 
        "dev_reset_token": token
    }