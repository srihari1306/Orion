from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class OrderStatus(str, enum.Enum):
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    returned = "returned"
    cancelled = "cancelled"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(30), unique=True, index=True, nullable=False)  # e.g. ORD-1042
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    items = Column(JSON, default=list)           # [{"name": "...", "qty": 1, "price": 29.99}]
    total_amount = Column(Float, nullable=False)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.processing, nullable=False)
    tracking_number = Column(String(40), nullable=True)
    carrier = Column(String(40), nullable=True)
    is_delayed = Column(Boolean, default=False)
    delay_reason = Column(String(120), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)
    refunded = Column(Boolean, default=False)
    refund_amount = Column(Float, nullable=True)

    customer = relationship("User", foreign_keys=[customer_id])

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tier = Column(String(20), default="standard")          # free | standard | premium | enterprise
    lifetime_value = Column(Float, default=0.0)
    churn_risk = Column(Float, default=0.2)
    account_age_days = Column(Integer, default=0)
    satisfaction_score = Column(Float, default=4.0)
    abuse_score = Column(Float, default=0.0)               # 0.0 = clean, 1.0 = high risk
    refunds_last_30_days = Column(Integer, default=0)
    prior_refund_in_30d = Column(Boolean, default=False)
    outstanding_balance = Column(Float, default=0.0)
    payment_method = Column(String(30), default="card")

    customer = relationship("User", foreign_keys=[customer_id])
