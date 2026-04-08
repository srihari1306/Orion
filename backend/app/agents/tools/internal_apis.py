import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.order import Order, CustomerProfile, OrderStatus

def _get_db() -> Session:
    return SessionLocal()

async def fetch_crm_data(customer_id: int) -> dict:
    await asyncio.sleep(0)
    db = _get_db()
    try:
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer_id
        ).first()

        if not profile:
            return {
                "customer_id": customer_id,
                "tier": "standard",
                "lifetime_value": 0.0,
                "churn_risk": 0.2,
                "account_age_days": 0,
                "satisfaction_score": 4.0,
            }

        return {
            "customer_id": customer_id,
            "tier": profile.tier,
            "lifetime_value": profile.lifetime_value,
            "churn_risk": profile.churn_risk,
            "account_age_days": profile.account_age_days,
            "satisfaction_score": profile.satisfaction_score,
        }
    finally:
        db.close()

async def fetch_order_data(customer_id: int, order_id: str = None) -> dict:
    await asyncio.sleep(0)
    db = _get_db()
    try:
        query = db.query(Order).filter(Order.customer_id == customer_id)

        if order_id:
            order = query.filter(Order.order_id == order_id).first()
        else:
            order = query.order_by(Order.order_date.desc()).first()

        if not order:
            return {
                "order_id": order_id or "NOT_FOUND",
                "status": "not_found",
                "items": [],
                "total_amount": 0.0,
                "order_date": None,
                "fulfillment_state": "unknown",
                "found": False,
            }

        return {
            "order_id": order.order_id,
            "status": order.status.value,
            "items": order.items or [],
            "total_amount": order.total_amount,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "fulfillment_state": "fulfilled" if order.status == OrderStatus.delivered else "pending",
            "refunded": order.refunded,
            "refund_amount": order.refund_amount,
            "found": True,
        }
    finally:
        db.close()

async def fetch_billing_data(customer_id: int) -> dict:
    await asyncio.sleep(0)
    db = _get_db()
    try:
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer_id
        ).first()

        if not profile:
            return {
                "customer_id": customer_id,
                "outstanding_balance": 0.0,
                "refunds_last_30_days": 0,
                "credits_issued": 0.0,
                "payment_method": "card",
                "abuse_score": 0.0,
                "prior_refund_in_30d": False,
            }

        return {
            "customer_id": customer_id,
            "outstanding_balance": profile.outstanding_balance,
            "refunds_last_30_days": profile.refunds_last_30_days,
            "credits_issued": 0.0,
            "payment_method": profile.payment_method,
            "abuse_score": profile.abuse_score,
            "prior_refund_in_30d": profile.prior_refund_in_30d,
        }
    finally:
        db.close()

async def fetch_shipping_data(customer_id: int, order_id: str = None) -> dict:
    await asyncio.sleep(0)
    db = _get_db()
    try:
        query = db.query(Order).filter(Order.customer_id == customer_id)
        if order_id:
            order = query.filter(Order.order_id == order_id).first()
        else:
            order = query.order_by(Order.order_date.desc()).first()

        if not order or not order.tracking_number:
            return {
                "tracking_number": None,
                "carrier": None,
                "estimated_delivery": None,
                "last_scan": None,
                "delay_reason": None,
                "is_delayed": False,
            }

        return {
            "tracking_number": order.tracking_number,
            "carrier": order.carrier,
            "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
            "last_scan": None,
            "delay_reason": order.delay_reason,
            "is_delayed": order.is_delayed,
        }
    finally:
        db.close()

async def fetch_all_context(customer_id: int, order_id: str = None) -> dict:
    crm, order, billing, shipping = await asyncio.gather(
        fetch_crm_data(customer_id),
        fetch_order_data(customer_id, order_id),
        fetch_billing_data(customer_id),
        fetch_shipping_data(customer_id, order_id),
    )
    return {"crm": crm, "order": order, "billing": billing, "shipping": shipping}

async def issue_refund(customer_id: int, amount: float, order_id: str) -> dict:
    await asyncio.sleep(0)
    db = _get_db()
    try:
        order = db.query(Order).filter(
            Order.order_id == order_id,
            Order.customer_id == customer_id,
        ).first()

        if not order:
            return {"success": False, "error": f"Order {order_id} not found"}

        if order.refunded:
            return {"success": False, "error": "Order already refunded"}

        order.refunded = True
        order.refund_amount = amount
        order.status = OrderStatus.returned

        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer_id
        ).first()
        if profile:
            profile.refunds_last_30_days += 1
            profile.prior_refund_in_30d = True

        db.commit()
        return {
            "success": True,
            "refund_id": f"REF-{order.id:05d}",
            "amount": amount,
            "order_id": order_id,
            "eta_days": 3,
            "message": f"Refund of ${amount:.2f} processed successfully",
        }
    finally:
        db.close()

async def issue_credit(customer_id: int, amount: float) -> dict:
    await asyncio.sleep(0)
    return {
        "success": True,
        "credit_id": f"CRD-{customer_id:05d}",
        "amount": amount,
        "message": f"${amount:.2f} store credit applied to account",
    }

async def trigger_replacement(order_id: str, items: list) -> dict:
    await asyncio.sleep(0)
    db = _get_db()
    try:
        original = db.query(Order).filter(Order.order_id == order_id).first()
        if not original:
            return {"success": False, "error": f"Order {order_id} not found"}

        if original.status == OrderStatus.returned:
            return {"success": False, "error": f"Order {order_id} has already been returned/replaced"}

        max_order = db.query(Order).order_by(Order.id.desc()).first()
        next_num = (max_order.id + 1) if max_order else 1
        new_order_id = f"ORD-R{next_num:04d}"

        replacement = Order(
            order_id=new_order_id,
            customer_id=original.customer_id,
            items=original.items,
            total_amount=original.total_amount,
            status=OrderStatus.processing,
            order_date=datetime.utcnow(),
            estimated_delivery=datetime.utcnow() + timedelta(days=2),
        )
        db.add(replacement)
        original.status = OrderStatus.returned
        db.commit()

        return {
            "success": True,
            "replacement_order_id": new_order_id,
            "original_order_id": order_id,
            "ships_in_days": 2,
            "message": "Replacement order created and will ship within 2 business days",
        }
    finally:
        db.close()

async def reroute_shipment(tracking_number: str, new_address: str = None) -> dict:
    await asyncio.sleep(0)
    return {
        "success": True,
        "tracking_number": tracking_number,
        "rerouted": True,
        "message": "Shipment reroute request submitted to carrier",
    }
