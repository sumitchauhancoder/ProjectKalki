from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class VoiceMacro(Base):
    __tablename__ = "voice_macros"

    id = Column(Integer, primary_key=True, index=True)
    trigger_phrase = Column(String, unique=True, index=True)
    action_type = Column(String)  # 'launch_app', 'hotkey', 'type_text'
    action_payload = Column(Text)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    command_input = Column(String)
    execution_status = Column(String)
    telemetry_data = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_title = Column(String, default="Default Session")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)      # 'user' or 'assistant'
    content = Column(Text)     # message text
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")