from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.models.action_log import ActionLog
from app.core.security import require_roles, hash_password
from sqlalchemy import func

router = APIRouter(prefix="/admin", tags=["Admin"])

class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    users = db.query(User).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at}
        for u in users
    ]

@router.post("/users", status_code=201)
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(name=req.name, email=req.email, password_hash=hash_password(req.password), role=req.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"message": f"User {user_id} deactivated"}

@router.get("/stats")
def system_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager")),
):
    total_tickets = db.query(Ticket).count()
    resolved = db.query(Ticket).filter(Ticket.status == "resolved").count()
    pending = db.query(Ticket).filter(Ticket.status == "pending_approval").count()
    escalated = db.query(Ticket).filter(Ticket.status == "escalated").count()
    open_count = db.query(Ticket).filter(Ticket.status == "open").count()
    total_actions = db.query(ActionLog).count()

    resolution_rate = round((resolved / total_tickets * 100), 1) if total_tickets else 0

    intents = (
        db.query(Ticket.intent, func.count(Ticket.intent))
        .group_by(Ticket.intent)
        .all()
    )

    return {
        "total_tickets": total_tickets,
        "open": open_count,
        "pending_approval": pending,
        "resolved": resolved,
        "escalated": escalated,
        "resolution_rate": resolution_rate,
        "total_actions_executed": total_actions,
        "intent_distribution": {intent: count for intent, count in intents if intent},
    }

@router.get("/audit-log")
def audit_log(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager")),
):
    logs = db.query(ActionLog).order_by(ActionLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "ticket_id": l.ticket_id,
            "action_type": l.action_type,
            "payload": l.payload,
            "executed_by": l.executed_by,
            "status": l.status,
            "result": l.result,
            "created_at": l.created_at,
        }
        for l in logs
    ]
