from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    macros = relationship("VoiceMacro", back_populates="owner")
    logs = relationship("AuditLog", back_populates="user")

class VoiceMacro(Base):
    __tablename__ = "voice_macros"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    trigger_phrase = Column(String(100), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # e.g., 'hotkey', 'launch_app', 'script'
    action_payload = Column(JSON, nullable=False)     # e.g., {"keys": ["win", "r"], "type": "notepad\n"}
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="macros")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    command_input = Column(Text, nullable=False)
    execution_status = Column(String(50), nullable=False)
    telemetry_data = Column(JSON, nullable=True)     # Stores vision/bounding box snapshot metadata
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")