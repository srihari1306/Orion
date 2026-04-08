from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.order import Order
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("/")
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "customer":
        orders = db.query(Order).order_by(Order.order_date.desc()).all()
    else:
        orders = (
            db.query(Order)
            .filter(Order.customer_id == current_user.id)
            .order_by(Order.order_date.desc())
            .all()
        )

    return [
        {
            "order_id": o.order_id,
            "items": o.items or [],
            "total_amount": o.total_amount,
            "status": o.status,
            "order_date": o.order_date,
            "estimated_delivery": o.estimated_delivery,
            "tracking_number": o.tracking_number,
            "refunded": o.refunded,
        }
        for o in orders
    ]

@router.get("/{order_id}")
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == "customer" and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "order_id": order.order_id,
        "items": order.items or [],
        "total_amount": order.total_amount,
        "status": order.status,
        "order_date": order.order_date,
        "estimated_delivery": order.estimated_delivery,
        "tracking_number": order.tracking_number,
        "carrier": order.carrier,
        "is_delayed": order.is_delayed,
        "delay_reason": order.delay_reason,
        "refunded": order.refunded,
        "refund_amount": order.refund_amount,
    }
