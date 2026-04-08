import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from app.database import create_all_tables, SessionLocal, drop_all_tables
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, CustomerProfile
from app.core.security import hash_password

DEMO_USERS = [
    {"name": "Alice Customer", "email": "customer@demo.com", "password": "demo1234", "role": UserRole.customer},
    {"name": "Bob Agent", "email": "agent@demo.com", "password": "demo1234", "role": UserRole.agent},
    {"name": "Carol Manager", "email": "manager@demo.com", "password": "demo1234", "role": UserRole.manager},
    {"name": "Dave Admin", "email": "admin@demo.com", "password": "demo1234", "role": UserRole.admin},
]

DEMO_ORDERS = [
    {
        "order_id": "ORD-1001",
        "items": [{"name": "Wireless Bluetooth Headphones", "qty": 1, "price": 49.99}],
        "total_amount": 49.99,
        "status": OrderStatus.delivered,
        "tracking_number": "TRK-7781001",
        "carrier": "FedEx",
        "is_delayed": False,
        "order_date": datetime.utcnow() - timedelta(days=14),
        "estimated_delivery": datetime.utcnow() - timedelta(days=7),
    },
    {
        "order_id": "ORD-1002",
        "items": [{"name": "Ergonomic Laptop Stand", "qty": 1, "price": 89.99}, {"name": "USB-C Hub", "qty": 1, "price": 34.99}],
        "total_amount": 124.98,
        "status": OrderStatus.delivered,
        "tracking_number": "TRK-7781002",
        "carrier": "UPS",
        "is_delayed": False,
        "order_date": datetime.utcnow() - timedelta(days=10),
        "estimated_delivery": datetime.utcnow() - timedelta(days=4),
    },
    {
        "order_id": "ORD-1003",
        "items": [{"name": "Premium Laptop Stand (Glass Top)", "qty": 1, "price": 179.99}],
        "total_amount": 179.99,
        "status": OrderStatus.delivered,
        "tracking_number": "TRK-7781003",
        "carrier": "UPS",
        "is_delayed": False,
        "order_date": datetime.utcnow() - timedelta(days=5),
        "estimated_delivery": datetime.utcnow() - timedelta(days=1),
    },
    {
        "order_id": "ORD-1004",
        "items": [{"name": "Mechanical Keyboard", "qty": 1, "price": 129.99}],
        "total_amount": 129.99,
        "status": OrderStatus.shipped,
        "tracking_number": "TRK-7781004",
        "carrier": "USPS",
        "is_delayed": True,
        "delay_reason": "Weather delay at regional hub",
        "order_date": datetime.utcnow() - timedelta(days=3),
        "estimated_delivery": datetime.utcnow() + timedelta(days=2),
    },
    {
        "order_id": "ORD-1005",
        "items": [{"name": "Webcam HD Pro", "qty": 1, "price": 59.99}],
        "total_amount": 59.99,
        "status": OrderStatus.processing,
        "tracking_number": None,
        "carrier": None,
        "is_delayed": False,
        "order_date": datetime.utcnow() - timedelta(days=1),
        "estimated_delivery": datetime.utcnow() + timedelta(days=5),
    },
]

ALICE_PROFILE = {
    "tier": "standard",
    "lifetime_value": 544.94,
    "churn_risk": 0.15,
    "account_age_days": 240,
    "satisfaction_score": 4.2,
    "abuse_score": 0.05,
    "refunds_last_30_days": 0,
    "prior_refund_in_30d": False,
    "outstanding_balance": 0.0,
    "payment_method": "card",
}

def seed():
    print("Creating tables...")
    drop_all_tables()
    create_all_tables()
    db = SessionLocal()
    try:
        alice_id = None

        for u in DEMO_USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                user = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=hash_password(u["password"]),
                    role=u["role"],
                )
                db.add(user)
                db.flush()
                print(f"  ✓ Created {u['role']}: {u['email']} (id={user.id})")
                if u["email"] == "customer@demo.com":
                    alice_id = user.id
            else:
                print(f"  – Already exists: {u['email']}")
                if u["email"] == "customer@demo.com":
                    alice_id = existing.id

        if alice_id:
            profile = CustomerProfile(
                customer_id=alice_id,
                **ALICE_PROFILE,
            )
            db.add(profile)
            print(f"  ✓ Created customer profile for Alice (customer_id={alice_id})")

            for o in DEMO_ORDERS:
                order = Order(
                    customer_id=alice_id,
                    **o,
                )
                db.add(order)
                print(f"  ✓ Created order {o['order_id']}: ${o['total_amount']:.2f} ({o['status'].value})")

        db.commit()
        print("\n── Seed complete! ──")
        print("Password for all:  demo1234")
        print(f"\nAlice's orders:")
        print(f"  ORD-1001  $49.99   Wireless Headphones     (delivered)")
        print(f"  ORD-1002  $124.98  Laptop Stand + USB Hub  (delivered)")
        print(f"  ORD-1003  $179.99  Premium Laptop Stand    (delivered)")
        print(f"  ORD-1004  $129.99  Mechanical Keyboard     (shipped, delayed)")
        print(f"  ORD-1005  $59.99   Webcam HD Pro           (processing)")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
