from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.message import Message
from app.models.user import User
from app.core.security import get_current_user, require_roles
from datetime import datetime

router = APIRouter(prefix="/tickets", tags=["Tickets"])

_sio = None

def set_sio(socket_instance):
    global _sio
    _sio = socket_instance

class CreateTicketRequest(BaseModel):
    subject: str
    message: Optional[str] = None
    order_id: Optional[str] = None  # customer can optionally link an order

class TicketOut(BaseModel):
    id: int
    subject: str
    status: str
    priority: str
    intent: Optional[str]
    sentiment_score: Optional[str]
    resolution_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.post("/", status_code=201)
def create_ticket(
    req: CreateTicketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = Ticket(
        customer_id=current_user.id,
        subject=req.subject,
        order_id=req.order_id,
        status=TicketStatus.open,
        priority=TicketPriority.P2,
    )
    db.add(ticket)
    db.flush()  # get ticket.id

    if req.message:
        msg = Message(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            content=req.message,
            is_ai=False,
        )
        db.add(msg)

    db.commit()
    db.refresh(ticket)
    return {"ticket_id": ticket.id, "status": ticket.status, "message": "Ticket created. Orion is analyzing..."}

@router.get("/")
def list_tickets(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Ticket)
    if current_user.role == "customer":
        query = query.filter(Ticket.customer_id == current_user.id)
    if status:
        query = query.filter(Ticket.status == status)
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "intent": t.intent,
            "resolution_type": t.resolution_type,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "customer_id": t.customer_id,
        }
        for t in tickets
    ]

@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = db.query(Message).filter(Message.ticket_id == ticket_id).order_by(Message.created_at).all()
    return {
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "intent": ticket.intent,
            "sentiment_score": ticket.sentiment_score,
            "confidence_score": ticket.confidence_score,
            "resolution_type": ticket.resolution_type,
            "summary": ticket.summary,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        },
        "messages": [
            {
                "id": m.id,
                "content": m.content,
                "is_ai": m.is_ai,
                "sender_id": m.sender_id,
                "created_at": m.created_at,
                "metadata": m.metadata_,
            }
            for m in messages
        ],
    }

@router.patch("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.assigned_to = agent_id
    db.commit()
    return {"message": f"Ticket {ticket_id} assigned to agent {agent_id}"}

class ResolveRequest(BaseModel):
    resolution_note: Optional[str] = None

@router.post("/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: int,
    req: ResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "manager", "admin")),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status == TicketStatus.resolved:
        raise HTTPException(status_code=400, detail="Ticket is already resolved")

    ticket.status = TicketStatus.resolved
    ticket.updated_at = datetime.utcnow()

    agent_name = current_user.name or "a support specialist"
    
    if req.resolution_note and req.resolution_note.strip():
        reply_text = req.resolution_note.strip()
    else:
        reply_text = f"This ticket has been resolved by {agent_name}."

    ai_msg = Message(
        ticket_id=ticket_id,
        sender_id=None,
        content=reply_text,
        is_ai=True,
        metadata_={
            "resolution_path": "manual_resolve",
            "resolved_by": current_user.id,
            "steps_taken": ["agent_resolved"],
        },
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    if _sio:
        import asyncio
        try:
            asyncio.run(_sio.emit("ticket_update", {
                "ticket_id": ticket_id,
                "status": "resolved",
                "resolution_path": "manual_resolve",
                "reply": reply_text,
                "steps_taken": ["agent_resolved"],
            }))
        except Exception:
            pass

    return {"message": "Ticket resolved", "ticket_id": ticket_id, "reply": reply_text}
