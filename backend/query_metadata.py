from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from app.models.message import Message

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

messages = db.query(Message).order_by(Message.id.desc()).limit(2).all()

for msg in messages:
    print(f"Message ID: {msg.id}, is_ai: {msg.is_ai}")
    print(f"Content: {msg.content}")
    print(f"Metadata: {msg.metadata_}")
    print("-" * 40)
