from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.action_log import ApprovalRequest, ApprovalStatus, ActionLog, ActionType, ActionStatus
from app.models.ticket import Ticket, TicketStatus
from app.core.security import require_roles
from app.models.user import User

router = APIRouter(prefix="/approve", tags=["Approvals"])

class ReviewRequest(BaseModel):
    status: str  # "approved" or "rejected"
    review_note: Optional[str] = None

@router.get("/")
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    approvals = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.status == ApprovalStatus.pending)
        .order_by(ApprovalRequest.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "ticket_id": a.ticket_id,
            "action_type": a.action_type,
            "payload": a.payload,
            "briefing": a.briefing,
            "created_at": a.created_at,
        }
        for a in approvals
    ]

import asyncio
from app.agents.tools.internal_apis import issue_refund, issue_credit, trigger_replacement, reroute_shipment
from app.models.message import Message

sio = None

def set_sio(socketio_instance):
    global sio
    sio = socketio_instance

@router.post("/{approval_id}/review")
def review_approval(
    approval_id: int,
    req: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    global sio
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail="Approval already reviewed")

    approval.status = ApprovalStatus.approved if req.status == "approved" else ApprovalStatus.rejected
    approval.reviewed_by = current_user.id
    approval.review_note = req.review_note
    approval.reviewed_at = datetime.utcnow()

    ticket = db.query(Ticket).filter(Ticket.id == approval.ticket_id).first()
    
    reply_text = ""

    if req.status == "approved":
        action_type = approval.action_type.value if hasattr(approval.action_type, "value") else approval.action_type
        payload = approval.payload or {}
        order_id = payload.get("order_id")
        amount = payload.get("amount")
        
        result_payload = {}
        if action_type == "refund" and order_id and amount:
            result_payload = asyncio.run(issue_refund(ticket.customer_id, amount, order_id))
        elif action_type == "credit" and ticket.customer_id and amount:
            result_payload = asyncio.run(issue_credit(ticket.customer_id, amount))
        elif action_type == "replacement" and order_id:
            result_payload = asyncio.run(trigger_replacement(order_id, []))
        elif action_type == "reroute":
            tracking = payload.get("tracking_number", order_id)
            result_payload = asyncio.run(reroute_shipment(tracking, payload.get("new_address")))

        try:
            action_type_enum = ActionType(action_type)
        except ValueError:
            action_type_enum = ActionType.closure

        log = ActionLog(
            ticket_id=approval.ticket_id,
            action_type=action_type_enum,
            payload=approval.payload,
            executed_by=f"manager:{current_user.id}",
            status=ActionStatus.executed if result_payload.get("success") else ActionStatus.failed,
            result=str(result_payload),
        )
        db.add(log)
        if ticket:
            ticket.status = TicketStatus.resolved
            ticket.resolution_type = "approval"
            
        reply_text = f"Good news! Your request has been approved by our management team and the action ({action_type}) has been processed successfully."
        if req.review_note and req.review_note.strip():
            reply_text += f" {req.review_note.strip()}"
        reply_text += " Let us know if you need any further assistance!"

    else:
        if ticket:
            ticket.status = TicketStatus.escalated  # Hand it back to an agent to explain why it was rejected
            
        reply_text = "Your request has been reviewed but could not be approved at this time. An agent will be in touch shortly to discuss further options."

    if ticket:
        ai_message = Message(
            ticket_id=ticket.id,
            sender_id=None,
            content=reply_text,
            is_ai=True,
            metadata_={"resolution_path": "approval" if req.status == "approved" else "escalated"}
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        
        if sio:
            asyncio.run(sio.emit("ticket_update", {
                "ticket_id": ticket.id,
                "status": ticket.status.value if hasattr(ticket.status, "value") else ticket.status,
                "resolution_path": ticket.resolution_type,
                "reply": reply_text
            }))
    else:
        db.commit()

    return {"message": f"Approval {req.status}", "ticket_id": approval.ticket_id}
