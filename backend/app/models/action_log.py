from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class ActionType(str, enum.Enum):
    refund = "refund"
    credit = "credit"
    replacement = "replacement"
    reroute = "reroute"
    escalation = "escalation"
    closure = "closure"
    follow_up = "follow_up"


class ActionStatus(str, enum.Enum):
    pending = "pending"
    executed = "executed"
    failed = "failed"
    reversed = "reversed"


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    action_type = Column(SAEnum(ActionType), nullable=False)
    payload = Column(JSON, nullable=True)
    executed_by = Column(String(50), default="orion-agent")  # agent name or user ID
    status = Column(SAEnum(ActionStatus), default=ActionStatus.executed)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="action_logs")


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    briefing = Column(Text, nullable=True)
    status = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.pending)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    ticket = relationship("Ticket", back_populates="approval_requests")
