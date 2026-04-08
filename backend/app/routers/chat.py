import asyncio
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.message import Message
from app.models.action_log import ActionLog, ApprovalRequest, ActionType, ActionStatus
from app.models.user import User
from app.core.security import get_current_user
from app.core.resilience import with_timeout

logger = logging.getLogger("orion.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])

sio = None

def set_sio(socket_instance):
    global sio
    sio = socket_instance

class SendMessageRequest(BaseModel):
    ticket_id: int
    content: str

def _run_agent_and_persist(ticket_id: int, customer_id: int, content: str, db_url: str, ticket_subject: str, linked_order_id: str = None):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.agents.graph import run_orion

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        prior_msgs = (
            db.query(Message)
            .filter(Message.ticket_id == ticket_id, Message.is_ai == True)
            .order_by(Message.created_at.desc())
            .limit(3)
            .all()
        )
        prior_context = "\n".join([m.content for m in reversed(prior_msgs)]) if prior_msgs else None

        if linked_order_id and linked_order_id not in content:
            content_with_order = f"[Order: {linked_order_id}] {content}"
        else:
            content_with_order = content

        if sio:
            try:
                asyncio.run(sio.emit("agent_thinking", {
                    "ticket_id": ticket_id,
                    "step": "triage",
                    "message": "Orion is analyzing your request...",
                }))
            except Exception:
                pass

        async def _run_with_timeout():
            return await with_timeout(
                asyncio.to_thread(
                    run_orion,
                    ticket_id=ticket_id,
                    customer_id=customer_id,
                    raw_text=content_with_order,
                    channel="chat",
                    prior_context=prior_context,
                    linked_order_id=linked_order_id,
                ),
                seconds=30.0,
            )

        result = asyncio.run(_run_with_timeout())

        ai_message = Message(
            ticket_id=ticket_id,
            sender_id=None,
            content=result.get("reply_text", "Processing complete."),
            is_ai=True,
            metadata_={
                "intent": result.get("intent"),
                "sentiment_score": result.get("sentiment_score"),
                "urgency": result.get("urgency"),
                "confidence_score": result.get("confidence_score"),
                "resolution_path": result.get("resolution_path"),
                "steps_taken": result.get("steps_taken", []),
                "entities": result.get("entities"),
            },
        )
        db.add(ai_message)

        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket:
            ticket.intent = result.get("intent")
            ticket.sentiment_score = str(result.get("sentiment_score", 0.0))
            ticket.confidence_score = str(result.get("confidence_score", 0.5))
            ticket.resolution_type = result.get("resolution_path")

            val_order_id = result.get("entities", {}).get("order_id")
            if val_order_id and not ticket.order_id:
                ticket.order_id = val_order_id

            urgency_map = {"P0": TicketPriority.P0, "P1": TicketPriority.P1, "P2": TicketPriority.P2, "P3": TicketPriority.P3}
            ticket.priority = urgency_map.get(result.get("urgency", "P2"), TicketPriority.P2)

            resolution_path = result.get("resolution_path", "handoff")

            if resolution_path == "auto_resolve":
                ticket.status = TicketStatus.resolved
                action_plan = result.get("action_plan") or {}
                if action_plan.get("action_type"):
                    try:
                        action_type_enum = ActionType(action_plan["action_type"])
                    except ValueError:
                        action_type_enum = ActionType.closure
                    log = ActionLog(
                        ticket_id=ticket_id,
                        action_type=action_type_enum,
                        payload={
                            "amount": action_plan.get("amount"),
                            "order_id": action_plan.get("order_id"),
                            "reason": action_plan.get("reason"),
                        },
                        executed_by="orion-agent",
                        status=ActionStatus.executed,
                        result=str(result.get("action_result", {})),
                    )
                    db.add(log)

            elif resolution_path == "need_info":
                ticket.status = TicketStatus.open

            elif resolution_path == "approval":
                ticket.status = TicketStatus.pending_approval
                action_plan = result.get("action_plan") or {}
                approval = ApprovalRequest(
                    ticket_id=ticket_id,
                    action_type=action_plan.get("action_type", "unknown"),
                    payload=action_plan,
                    briefing=result.get("briefing", ""),
                )
                db.add(approval)

            elif resolution_path == "handoff":
                ticket.status = TicketStatus.escalated
                ticket.summary = result.get("briefing", "")[:500] if result.get("briefing") else None

        db.commit()

        if sio:
            import asyncio
            try:
                asyncio.run(sio.emit("ticket_update", {
                    "ticket_id": ticket_id,
                    "status": ticket.status if ticket else "unknown",
                    "resolution_path": result.get("resolution_path"),
                    "reply": result.get("reply_text"),
                    "steps_taken": result.get("steps_taken", []),
                }))
            except Exception:
                pass

    except Exception as e:
        db.rollback()
        logger.error(f"[Pipeline] Total pipeline failure for ticket {ticket_id}: {e}")

        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if ticket:
                ticket.status = TicketStatus.escalated
                ticket.resolution_type = "handoff"
                ticket.summary = f"Auto-escalated: pipeline failure — {str(e)[:200]}"

            error_msg = Message(
                ticket_id=ticket_id,
                sender_id=None,
                content=(
                    "We're experiencing a brief technical issue processing your request. "
                    "A human specialist has been notified and will follow up with you shortly. "
                    "We appreciate your patience!"
                ),
                is_ai=True,
                metadata_={
                    "error": str(e),
                    "pipeline_failure": True,
                    "auto_escalated": True,
                },
            )
            db.add(error_msg)
            db.commit()

            if sio:
                try:
                    asyncio.run(sio.emit("ticket_update", {
                        "ticket_id": ticket_id,
                        "status": "escalated",
                        "resolution_path": "handoff",
                        "reply": error_msg.content,
                        "steps_taken": ["pipeline_failure", "auto_escalated_to_human"],
                    }))
                except Exception:
                    pass

        except Exception as inner_e:
            logger.critical(f"[Pipeline] Failed to escalate ticket {ticket_id}: {inner_e}")
    finally:
        db.close()

@router.post("/send")
def send_message(
    req: SendMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == req.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if current_user.role != "customer":
        agent_msg = Message(
            ticket_id=req.ticket_id,
            sender_id=current_user.id,
            content=req.content,
            is_ai=True,  # Set to true so it aligns on the left for the customer
            metadata_={"sender_name": current_user.name, "is_agent_reply": True, "resolution_path": ticket.resolution_type}
        )
        db.add(agent_msg)
        db.commit()
        db.refresh(agent_msg)
        
        if sio:
            def _emit_agent_reply():
                import asyncio
                try:
                    asyncio.run(sio.emit("ticket_update", {
                        "ticket_id": ticket.id,
                        "status": ticket.status.value if hasattr(ticket.status, "value") else ticket.status,
                        "resolution_path": ticket.resolution_type,
                        "reply": req.content,
                        "metadata": {"sender_name": current_user.name, "is_agent_reply": True, "resolution_path": ticket.resolution_type}
                    }))
                except RuntimeError:
                    pass
            background_tasks.add_task(_emit_agent_reply)
            
        return {
            "message_id": agent_msg.id,
            "status": "sent",
            "message": "Message sent to customer.",
        }

    customer_msg = Message(
        ticket_id=req.ticket_id,
        sender_id=current_user.id,
        content=req.content,
        is_ai=False,
    )
    db.add(customer_msg)
    db.commit()
    db.refresh(customer_msg)

    if ticket.status in [TicketStatus.resolved, TicketStatus.closed]:
        ticket.status = TicketStatus.open
        ticket.resolution_type = None  # Clear previous resolution so AI can re-evaluate
        db.commit()

    if ticket.resolution_type == "handoff" or ticket.status == TicketStatus.pending_approval:
        if sio:
            def _emit_ack():
                import asyncio
                try:
                    asyncio.run(sio.emit("ticket_update", {
                        "ticket_id": ticket.id,
                        "status": ticket.status.value if hasattr(ticket.status, "value") else ticket.status,
                        "resolution_path": ticket.resolution_type,
                    }))
                except RuntimeError:
                    pass
            background_tasks.add_task(_emit_ack)

        return {
            "message_id": customer_msg.id,
            "status": "received_by_agent",
            "message": "Message saved to agent queue.",
        }

    from app.core.config import get_settings
    settings = get_settings()

    background_tasks.add_task(
        _run_agent_and_persist,
        ticket_id=req.ticket_id,
        customer_id=ticket.customer_id,
        content=req.content,
        db_url=settings.DATABASE_URL,
        ticket_subject=ticket.subject,
        linked_order_id=ticket.order_id,
    )

    return {
        "message_id": customer_msg.id,
        "status": "received",
        "message": "Orion is processing your request...",
    }
