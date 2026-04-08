import socketio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.database import create_all_tables
from app.models import User, Ticket, Message, ActionLog, ApprovalRequest  # noqa
from app.routers import auth, tickets, chat, approve, admin, orders, metrics

settings = get_settings()

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
    logger=False,
    engineio_logger=False,
)

@sio.event
async def connect(sid, environ, auth=None):
    print(f"[Socket.IO] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")

@sio.event
async def chat_message(sid, data):
    print(f"[Socket.IO] chat_message from {sid}: {data}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Orion starting up — creating tables...")
    create_all_tables()
    from app.routers.chat import set_sio as chat_set_sio
    from app.routers.tickets import set_sio as tickets_set_sio
    from app.routers.approve import set_sio as approve_set_sio
    chat_set_sio(sio)
    tickets_set_sio(sio)
    approve_set_sio(sio)
    print("Orion ready.")
    yield
    print("🛑 Orion shutting down.")

app = FastAPI(
    title="Orion — Autonomous Support Engine",
    description="AI-powered customer support resolution platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(chat.router)
app.include_router(approve.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(metrics.router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Orion", "version": "1.0.0"}

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    uvicorn.run("app.main:socket_app", host="0.0.0.0", port=8000, reload=True)
