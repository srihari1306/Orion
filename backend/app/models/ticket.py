from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class TicketStatus(str, enum.Enum):
    open = "open"
    pending_approval = "pending_approval"
    resolved = "resolved"
    closed = "closed"
    escalated = "escalated"

class TicketPriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject = Column(String(500), nullable=False)
    order_id = Column(String(30), nullable=True)  # linked order (e.g. ORD-1003)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.open)
    priority = Column(SAEnum(TicketPriority), default=TicketPriority.P2)
    summary = Column(Text, nullable=True)
    intent = Column(String(100), nullable=True)
    sentiment_score = Column(String(20), nullable=True)
    confidence_score = Column(String(20), nullable=True)
    resolution_type = Column(String(50), nullable=True)  # auto_resolve / approval / handoff
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("User", foreign_keys=[customer_id], back_populates="submitted_tickets")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tickets")
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")
    action_logs = relationship("ActionLog", back_populates="ticket", cascade="all, delete-orphan")
    approval_requests = relationship("ApprovalRequest", back_populates="ticket", cascade="all, delete-orphan")
