import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float
from app.database import get_db
from app.models.ticket import Ticket, TicketStatus
from app.models.message import Message
from app.models.action_log import ActionLog
from app.core.security import require_roles

logger = logging.getLogger("orion.metrics")

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/summary")
def get_metrics_summary(
    db: Session = Depends(get_db),
    _=Depends(require_roles("manager", "admin")),
):
    tickets = db.query(Ticket).all()
    total = len(tickets)

    if total == 0:
        return {
            "total_tickets": 0,
            "resolved_count": 0,
            "auto_resolution_rate": 0,
            "escalation_rate": 0,
            "approval_rate": 0,
            "need_info_rate": 0,
            "failure_rate": 0,
            "avg_resolution_time_minutes": 0,
            "avg_confidence_score": 0,
            "intent_distribution": {},
            "resolution_path_distribution": {},
            "priority_distribution": {},
            "fallback_triggered_count": 0,
            "pipeline_failure_count": 0,
        }

    resolved = [t for t in tickets if t.status in (
        TicketStatus.resolved, TicketStatus.closed
    )]
    auto_resolved = [t for t in resolved if t.resolution_type == "auto_resolve"]
    escalated = [t for t in tickets if t.resolution_type == "handoff"]
    approval = [t for t in tickets if t.resolution_type == "approval"]
    need_info = [t for t in tickets if t.resolution_type == "need_info"]

    times = []
    for t in resolved:
        if t.updated_at and t.created_at and t.updated_at > t.created_at:
            delta = (t.updated_at - t.created_at).total_seconds() / 60.0
            times.append(delta)
    avg_resolution_time = round(sum(times) / len(times), 1) if times else 0

    confidences = []
    for t in tickets:
        if t.confidence_score:
            try:
                confidences.append(float(t.confidence_score))
            except (ValueError, TypeError):
                pass
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0

    intent_counts = {}
    for t in tickets:
        if t.intent:
            intent_counts[t.intent] = intent_counts.get(t.intent, 0) + 1

    resolution_counts = {}
    for t in tickets:
        path = t.resolution_type or "unknown"
        resolution_counts[path] = resolution_counts.get(path, 0) + 1

    priority_counts = {}
    for t in tickets:
        p = t.priority.value if hasattr(t.priority, "value") else str(t.priority)
        if p:
            priority_counts[p] = priority_counts.get(p, 0) + 1

    all_ai_messages = db.query(Message).filter(Message.is_ai == True).all()

    fallback_count = 0
    pipeline_failure_count = 0
    for msg in all_ai_messages:
        meta = msg.metadata_ or {}
        steps = meta.get("steps_taken", [])
        if isinstance(steps, list):
            if any("fallback_used" in s for s in steps):
                fallback_count += 1
        if meta.get("pipeline_failure"):
            pipeline_failure_count += 1

    failed = [t for t in tickets
              if t.status not in (TicketStatus.resolved, TicketStatus.closed)
              and t.resolution_type == "handoff"]

    return {
        "total_tickets": total,
        "resolved_count": len(resolved),
        "auto_resolution_rate": round(len(auto_resolved) / total * 100, 1),
        "escalation_rate": round(len(escalated) / total * 100, 1),
        "approval_rate": round(len(approval) / total * 100, 1),
        "need_info_rate": round(len(need_info) / total * 100, 1),
        "failure_rate": round(pipeline_failure_count / total * 100, 1) if total else 0,
        "avg_resolution_time_minutes": avg_resolution_time,
        "avg_confidence_score": avg_confidence,
        "intent_distribution": intent_counts,
        "resolution_path_distribution": resolution_counts,
        "priority_distribution": priority_counts,
        "fallback_triggered_count": fallback_count,
        "pipeline_failure_count": pipeline_failure_count,
    }

@router.get("/health")
def agent_health(
    _=Depends(require_roles("manager", "admin")),
):
    from app.core.resilience import groq_breaker
    return {
        "circuit_state": groq_breaker.state.value,
        "failure_count": groq_breaker.failure_count,
        "failure_threshold": groq_breaker.failure_threshold,
        "is_open": groq_breaker.is_open,
    }

@router.post("/circuit-breaker/reset")
def reset_circuit_breaker(
    _=Depends(require_roles("admin")),
):
    from app.core.resilience import groq_breaker
    groq_breaker.reset()
    return {"status": "reset", "circuit_state": groq_breaker.state.value}
