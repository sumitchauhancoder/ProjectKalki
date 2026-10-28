from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from database import get_db
from models import User, AuditLog
from auth import require_admin, get_current_user

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

class UserStatusSchema(BaseModel):
    status: str  # "active" or "disabled"

class UserRoleSchema(BaseModel):
    role: str  # "admin" or "user"

@admin_router.get("/stats")
def get_admin_stats(
    admin_user: User = Depends(require_admin),
    db: Optional[Session] = Depends(get_db)
):
    """Returns overview platform statistics for administrators."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.status == "active").scalar() or 0
    disabled_users = db.query(func.count(User.id)).filter(User.status == "disabled").scalar() or 0

    today_start = datetime.combine(date.today(), datetime.min.time())
    commands_today = db.query(func.count(AuditLog.id)).filter(AuditLog.timestamp >= today_start).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "disabled_users": disabled_users,
        "commands_today": commands_today
    }

@admin_router.get("/users")
def get_admin_users(
    admin_user: User = Depends(require_admin),
    db: Optional[Session] = Depends(get_db)
):
    """Returns all registered users with account details."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    users = db.query(User).order_by(User.id.asc()).all()
    user_list = []
    total_commands = db.query(func.count(AuditLog.id)).scalar() or 0

    for u in users:
        user_list.append({
            "id": u.id,
            "name": u.name,
            "username": u.username,
            "email": u.email,
            "role": getattr(u, "role", "user") or "user",
            "status": getattr(u, "status", "active") or "active",
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "commands": total_commands if u.role == "admin" else 0
        })

    return {"users": user_list}

@admin_router.get("/users/{user_id}")
def get_admin_user_detail(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Optional[Session] = Depends(get_db)
):
    """Returns details and last 50 audit log actions for a specific user."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Last 50 audit logs (without message content for privacy)
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    recent_logs = []
    for log in logs:
        recent_logs.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "action_type": log.command_input[:20] if log.command_input else "command",
            "status": log.execution_status or "success"
        })

    return {
        "user": {
            "id": target_user.id,
            "name": target_user.name,
            "username": target_user.username,
            "email": target_user.email,
            "role": getattr(target_user, "role", "user") or "user",
            "status": getattr(target_user, "status", "active") or "active",
            "created_at": target_user.created_at.isoformat() if target_user.created_at else None,
            "last_login": target_user.last_login.isoformat() if target_user.last_login else None,
        },
        "logs": recent_logs
    }

@admin_router.post("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: UserStatusSchema,
    admin_user: User = Depends(require_admin),
    db: Optional[Session] = Depends(get_db)
):
    """Enables or disables a user account."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    new_status = payload.status.strip().lower()
    if new_status not in ("active", "disabled"):
        raise HTTPException(status_code=400, detail="Invalid status. Must be 'active' or 'disabled'.")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Guard: admin cannot disable own account
    if target_user.id == admin_user.id and new_status == "disabled":
        raise HTTPException(status_code=400, detail="You cannot disable your own administrator account.")

    target_user.status = new_status
    db.commit()

    return {
        "message": f"User status updated to {new_status}.",
        "user": {
            "id": target_user.id,
            "username": target_user.username,
            "status": target_user.status
        }
    }

@admin_router.post("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: UserRoleSchema,
    admin_user: User = Depends(require_admin),
    db: Optional[Session] = Depends(get_db)
):
    """Promotes or demotes a user role."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    new_role = payload.role.strip().lower()
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'.")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Guard: cannot demote the last admin
    if getattr(target_user, "role", "user") == "admin" and new_role != "admin":
        admin_count = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last remaining administrator.")

    target_user.role = new_role
    db.commit()

    return {
        "message": f"User role updated to {new_role}.",
        "user": {
            "id": target_user.id,
            "username": target_user.username,
            "role": target_user.role
        }
    }
