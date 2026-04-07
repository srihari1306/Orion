<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Groq-Llama_3.3_70B-8B5CF6?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
</p>

# Orion — Autonomous Support Engine

> **A production-grade, AI-driven customer support resolution platform that reads, triages, decides, acts, drafts a reply, and closes tickets — without human intervention on routine issues. Built with retry/fallback/timeout resilience, circuit breaker protection, and a full evaluation metrics dashboard.**

Orion is not a chatbot. It's a **multi-agent AI system** built on a LangGraph state machine that autonomously resolves customer support tickets end-to-end. When a customer submits a refund request, Orion doesn't just acknowledge it — it extracts the intent and entities, fetches the customer's CRM profile, order history, billing data, and shipping status in parallel, runs the request through a policy engine with hard guardrails, executes the refund against the real database if it's within policy, drafts an empathetic reply, and closes the ticket. The entire pipeline takes seconds.

For cases that fall outside policy (high-value refunds, suspected abuse, compliance-sensitive issues), Orion generates a structured briefing document so a human agent can resolve the case in one click rather than ten minutes.

**What makes this production-grade:** Every LLM call is wrapped with exponential-backoff retries, a circuit breaker, and hard timeouts. If the LLM is completely unreachable, keyword-based fallback classifiers and static reply templates keep the system running. Total pipeline failures auto-escalate tickets to a human queue — nothing fails silently.

---

## Key Capabilities

| Capability | Description |
|-----------|-------------|
| **Intent + Entity Extraction** | LLM-powered triage with keyword fallback: parses raw chat into `{intent: "refund_request", order_id: "ORD-1001", amount: 49.99, sentiment: -0.42}` |
| **Multi-System Context Assembly** | Parallel CRM, orders, billing, and shipping lookups from MySQL — synthesized into a single `CustomerContext` before any decision |
| **Policy-Gated Autonomous Action** | Executes refunds, credits, and replacements directly when within guardrails. Routes to manager approval when outside them |
| **Production Resilience** | 3x retry with exponential backoff → circuit breaker (trips after 5 failures) → keyword fallback classifiers → static template replies. Nothing fails silently |
| **30s Pipeline Timeout** | Hard timeout on the entire agent graph. If exceeded, the ticket auto-escalates to a human queue with a graceful customer message |
| **Evaluation Metrics Dashboard** | Auto-resolve rate, escalation rate, avg resolution time, confidence scores, intent/priority distributions, fallback counts, and circuit breaker health — all in a live Manager Portal tab |
| **Confidence-Aware Handoff** | When confidence is low, writes a full briefing for the human agent with recommended action, so they resolve in one click |
| **Memory Across Re-opens** | If a customer reopens a resolved ticket, the agent has full prior conversation context — doesn't start from scratch |
| **Real-Time Updates** | Socket.IO pushes live thinking indicators, resolution results, and agent messages to the customer's chat |
| **Role-Based Portals** | Four distinct dashboards for Customer, Agent, Manager, and Admin — each with scoped capabilities |
| **Full Audit Trail** | Every AI decision, action, fallback trigger, and pipeline failure is logged with timestamps, payloads, and execution status |

---

## Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                 FRONTEND (React + Vite)                 │
                    │                                                         │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
                    │  │ Customer │ │  Agent   │ │ Manager  │ │  Admin   │   │
                    │  │  Chat    │ │Dashboard │ │ Portal   │ │  Panel   │   │
                    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
                    └───────┼────────────┼────────────┼────────────┼──────────┘
                            │            │            │            │
                      HTTP + Socket.IO (WebSocket)    │     JWT + RBAC
                            │            │            │            │
┌───────────────────────────┼────────────┼────────────┼────────────┼──────────┐
│                     BACKEND (FastAPI + Socket.IO)                           │
│                                                                             │
│  ┌──────┐ ┌───────┐ ┌────┐ ┌───────┐ ┌─────┐ ┌──────┐ ┌─────────┐        │
│  │ Auth │ │Tickets│ │Chat│ │Approve│ │Admin│ │Orders│ │ Metrics │        │
│  └──┬───┘ └───┬───┘ └─┬──┘ └───┬───┘ └──┬──┘ └──┬───┘ └────┬────┘        │
│     │         │       │        │        │       │           │              │
│     │         │  ┌────▼────────────────────────────┐       │              │
│     │         │  │   LANGGRAPH AGENT PIPELINE      │       │              │
│     │         │  │   (30s timeout safety net)      │       │              │
│     │         │  │                                  │       │              │
│     │         │  │  Triage → Context → Decision     │       │              │
│     │         │  │           → Action → Reply       │       │              │
│     │         │  │                                  │       │              │
│     │         │  │  Each LLM node:                  │       │              │
│     │         │  │  retry(3x) → breaker → fallback  │       │              │
│     │         │  └────┬──────────────────┬──────────┘       │              │
│     │         │       │                  │                  │              │
│     │         │  ┌────▼─────┐     ┌──────▼──────┐          │              │
│     │         │  │   Groq   │     │   MySQL DB  │          │              │
│     │         │  │ Llama 3.3│     │  (Real data)│          │              │
│     │         │  └──────────┘     └─────────────┘          │              │
│  ┌──┴─────────┴─────────────────────────────────────────────┴──┐           │
│  │                   RESILIENCE LAYER                          │           │
│  │  CircuitBreaker ← with_retry ← with_timeout ← fallbacks   │           │
│  └─────────────────────────────────────────────────────────────┘           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Production Resilience

Orion is designed so that **no ticket ever fails silently**. Every LLM call is protected by a three-layer resilience stack, and the entire pipeline has a safety net.

### Resilience Stack (per LLM node)

```
  Request
    │
    ▼
┌──────────────────┐
│  @with_retry     │ ← 3 attempts, exponential backoff (1.5s, 3s, 6s)
│  max_attempts=3  │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  @groq_breaker   │ ← Trips OPEN after 5 consecutive failures
│  CircuitBreaker  │   Rejects calls for 60s, then probes with HALF_OPEN
└────────┬─────────┘
         │
┌────────▼─────────┐
│  with_timeout    │ ← 10-12s hard timeout per LLM call
│  seconds=10.0    │
└────────┬─────────┘
         │
    Success? ──yes──▶ Return result
         │
        no
         │
┌────────▼─────────┐
│  Fallback        │ ← Keyword classifier (triage) / handoff (decision)
│  (per node)      │   / static template (reply)
└──────────────────┘
```

### Node-Level Fallbacks

| Node | Fallback When LLM Fails |
|------|------------------------|
| **Triage** | Keyword-based intent classifier (maps "refund", "broken", "shipping" → intent). Sets `confidence_score: 0.4` to flag low confidence |
| **Decision** | Auto-escalates to `handoff` (human agent). Safest possible default |
| **Reply** | Static reply templates per resolution path (need_info, auto_resolve, approval, handoff) |

### Graph-Level Safety Net

The entire pipeline is wrapped in a **30-second hard timeout**. If the pipeline crashes or times out:

1. Ticket status → `escalated`
2. Resolution type → `handoff`
3. Customer receives: *"We're experiencing a brief technical issue. A human specialist has been notified and will follow up shortly."*
4. Socket.IO emits the escalation event in real-time
5. Error is logged with full context for debugging

### Circuit Breaker States

| State | Behavior |
|-------|----------|
| **CLOSED** | Normal operation — requests pass through |
| **OPEN** | After 5 consecutive failures — all calls rejected for 60s |
| **HALF_OPEN** | After recovery timeout — one probe call allowed. Success → CLOSED, Failure → OPEN |

The circuit breaker can be monitored via `GET /metrics/health` and manually reset via `POST /metrics/circuit-breaker/reset` (admin only).

---

## Evaluation Metrics

Orion includes a production evaluation system that answers: *"Is the agent actually useful?"*

### Metrics API (`GET /metrics/summary`)

```json
{
  "total_tickets": 42,
  "resolved_count": 31,
  "auto_resolution_rate": 45.2,
  "escalation_rate": 23.8,
  "approval_rate": 19.0,
  "need_info_rate": 12.0,
  "failure_rate": 2.4,
  "avg_resolution_time_minutes": 3.7,
  "avg_confidence_score": 0.78,
  "intent_distribution": {
    "refund_request": 15,
    "wismo": 8,
    "general_inquiry": 12,
    "account_issue": 4,
    "replacement_request": 3
  },
  "resolution_path_distribution": {
    "auto_resolve": 19,
    "handoff": 10,
    "approval": 8,
    "need_info": 5
  },
  "priority_distribution": {"P0": 1, "P1": 8, "P2": 25, "P3": 8},
  "fallback_triggered_count": 3,
  "pipeline_failure_count": 1
}
```

### Manager Portal — Evaluation Dashboard

The Evaluation tab in the Manager Portal visualizes all metrics:

- **6 KPI Cards**: Auto-resolve rate, escalation rate, avg resolution time, avg confidence, fallback count, pipeline failures
- **Resolution Path Donut Chart**: Pure SVG visualization of auto_resolve vs handoff vs approval vs need_info
- **Intent Distribution**: Animated horizontal bar chart with per-intent colors
- **Priority Distribution**: P0–P3 breakdown bars
- **System Health Panel**: Live circuit breaker state (CLOSED/OPEN/HALF_OPEN), failure count vs threshold, fallback and failure counters

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **MySQL 8.0**
- **[Groq API Key](https://console.groq.com)** (free tier works)

### 1. Database Setup

Ensure you have a local MySQL 8.0 server running. Create the database:

```sql
CREATE DATABASE orion_db;
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env .env.local
# Edit .env and set your GROQ_API_KEY and DATABASE_URL

# Seed demo data (users, orders, customer profiles)
python seed.py

# Start the backend server
uvicorn app.main:socket_app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

Navigate to **[http://localhost:5173](http://localhost:5173)**

---

## Demo Accounts

| Role | Email | Password | Dashboard |
|------|-------|----------|-----------|
| **Customer** | `customer@demo.com` | `demo1234` | `/chat` — Submit tickets, chat with Orion AI |
| **Agent** | `agent@demo.com` | `demo1234` | `/agent` — Handle escalated tickets, send messages |
| **Manager** | `manager@demo.com` | `demo1234` | `/manager` — Approve/reject AI actions, view metrics dashboard |
| **Admin** | `admin@demo.com` | `demo1234` | `/admin` — User management, audit logs, system stats |

### Demo Orders (Alice Customer)

| Order ID | Amount | Items | Status |
|----------|--------|-------|--------|
| `ORD-1001` | $49.99 | Wireless Bluetooth Headphones | Delivered |
| `ORD-1002` | $124.98 | Ergonomic Laptop Stand + USB-C Hub | Delivered |
| `ORD-1003` | $179.99 | Premium Laptop Stand (Glass Top) | Delivered |
| `ORD-1004` | $129.99 | Mechanical Keyboard | 🚚 Shipped (Delayed) |
| `ORD-1005` | $59.99 | Webcam HD Pro | Processing |

---

## Agent Pipeline (LangGraph)

The Orion agent is a **compiled LangGraph state machine** with five sequential nodes. Each node enriches a shared `AgentState` TypedDict and is protected by the resilience layer.

```
┌──────────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────────┐
│    TRIAGE    │───→│ CONTEXT  │───→│   DECISION   │──┬→│  ACTION  │───→│    REPLY     │───→ END
│              │    │          │    │              │  │ │          │    │              │
│ • Intent    │    │ • CRM    │    │ • Policy     │  │ │ • Refund │    │ • Draft      │
│ • Sentiment │    │ • Orders │    │ • Guards     │  │ │ • Credit │    │ • Persist    │
│ • Urgency   │    │ • Billing│    │ • LLM        │  │ │ • Replace│    │ • Update     │
│ • Entities  │    │ • Ship   │    │ • Safety     │  │ │ • Reroute│    │ • Close      │
│             │    │          │    │              │  │ │          │    │              │
│ Fallback:│    │ No LLM   │    │ Fallback: │  │ │ Pre-exec │    │ Fallback: │
│ Keywords    │    │ (DB only)│    │ → handoff    │  │ │ validate │    │ Templates   │
└──────────────┘    └──────────┘    └──────────────┘  │ └──────────┘    └──────────────┘
                                                      │
                                            Conditional routing
                                            (always → action)
```

### Policy Engine Rules

| Condition | Resolution Path |
|-----------|----------------|
| Refund < $75, not enterprise, abuse_score < 0.3, no prior refund in 30d | **Auto-Resolve** |
| Refund ≥ $75 OR enterprise tier | **Approval** (Manager review) |
| Amount mismatch (claimed ≠ actual) | **Approval** (Human review) |
| Order ID not provided | **Need Info** (Ask customer) |
| Order not found in database | **Need Info** (Verify order) |
| Abuse score ≥ 0.3 | **Handoff** (Human agent) |
| Account issue / Bug report | **Handoff** (Always) |
| General inquiry | **Auto-Resolve** (Informational) |
| LLM completely unreachable (triage) | **Keyword fallback** (confidence: 0.4) |
| LLM completely unreachable (decision) | **Handoff** (Auto-escalate) |
| Pipeline timeout (30s) | **Escalated** (Auto-escalate to human queue) |

---

## Role-Based Portals

### Customer Portal (`/chat`)
- Create support tickets with optional order linking
- Real-time AI-powered chat with thinking indicators
- View ticket status, priority, intent, confidence
- Receive instant notifications when agents resolve tickets

### Agent Dashboard (`/agent`)
- Filter tickets by status (escalated, open, pending, resolved)
- Read Orion's structured briefing documents
- Send direct messages to customers (bypasses AI pipeline)
- One-click ticket resolution with custom notes
- Real-time customer notification via Socket.IO

### Manager Portal (`/manager`)
- **Approval Queue**: Review AI-recommended actions before execution
  - See action type, amount, order ID, and Orion's reasoning
  - One-click approve (executes action) or reject (escalates to agent)
  - Add review notes visible in audit trail
- **KPI Dashboard**: Resolution rate, intent distribution, ticket stats
- **Evaluation Dashboard** *(NEW)*: Full agent performance analytics
  - Auto-resolve / escalation / approval rates
  - Average resolution time and LLM confidence
  - Resolution path donut chart + intent distribution bars
  - Circuit breaker health panel + fallback/failure counters

### Admin Panel (`/admin`)
- **System Stats**: Total tickets, open/resolved/escalated counts, resolution rate
- **User Management**: Create users, assign roles, deactivate accounts
- **Audit Log**: Complete trail of every AI and human action executed

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Get JWT token |
| `GET` | `/auth/me` | Current user info |

### Tickets
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/tickets/` | Create ticket (with optional `order_id`) |
| `GET` | `/tickets/` | List tickets (filtered by role) |
| `GET` | `/tickets/{id}` | Get ticket with messages |
| `PATCH` | `/tickets/{id}/assign` | Assign to agent (manager/admin) |
| `POST` | `/tickets/{id}/resolve` | Resolve ticket (agent/manager/admin) |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/send` | Send message (triggers AI pipeline for customers, 30s timeout) |

### Approvals
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/approve/` | List pending approvals (manager/admin) |
| `POST` | `/approve/{id}/review` | Approve or reject action |

### Metrics *(NEW)*
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/metrics/summary` | manager, admin | Full evaluation dashboard data (rates, times, distributions, fallbacks) |
| `GET` | `/metrics/health` | manager, admin | Groq circuit breaker status (state, failure count, threshold) |
| `POST` | `/metrics/circuit-breaker/reset` | admin only | Manually reset the circuit breaker |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/users` | List all users |
| `POST` | `/admin/users` | Create user |
| `PATCH` | `/admin/users/{id}/deactivate` | Deactivate user |
| `GET` | `/admin/stats` | System statistics |
| `GET` | `/admin/audit-log` | Full audit trail |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/orders/` | List orders (scoped by role) |
| `GET` | `/orders/{order_id}` | Get order details |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |

---

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/orion_db
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET=your_jwt_secret_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string (URL-encoded special chars) | Required |
| `GROQ_API_KEY` | API key from [Groq Console](https://console.groq.com) | Required |
| `JWT_SECRET` | Secret key for token signing | `orion_super_secret_jwt_key` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `1440` (24 hours) |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` |

---



## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend Framework** | React 19 + Vite 8 | Fast HMR, modern APIs |
| **State Management** | Zustand 5 | Minimal boilerplate, performant |
| **HTTP Client** | Axios | Interceptors for JWT auth |
| **Real-Time Client** | Socket.IO Client 4 | Bidirectional WebSocket |
| **UI Components** | Lucide React | Consistent icon set |
| **Charts** | SVG (custom) | Zero-dependency donut + bar charts |
| **Backend Framework** | FastAPI | Async-first, auto-docs |
| **ORM** | SQLAlchemy 2 | Reliable, flexible |
| **AI Orchestration** | LangGraph | Deterministic multi-agent flow |
| **LLM Interface** | LangChain + Groq | Fast inference (Llama 3.3 70B) |
| **Resilience** | Custom (resilience.py) | Retry, timeout, circuit breaker |
| **Auth** | python-jose + passlib (bcrypt) | Industry-standard JWT + hashing |
| **Real-Time Server** | python-socketio | WebSocket with ASGI |
| **Database** | MySQL 8.0 | ACID-compliant, production-ready |


---

## Project Structure

```
Orion/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py              # LangGraph state machine
│   │   │   ├── state.py              # AgentState TypedDict
│   │   │   ├── nodes/
│   │   │   │   ├── triage_node.py    # Intent extraction (LLM + keyword fallback)
│   │   │   │   ├── context_node.py   # Parallel data fetch (DB only)
│   │   │   │   ├── decision_node.py  # Policy engine (LLM + guardrails + handoff fallback)
│   │   │   │   ├── action_node.py    # Execute refund/credit/replace
│   │   │   │   └── reply_node.py     # Draft reply (LLM + static template fallback)
│   │   │   └── tools/
│   │   │       └── internal_apis.py  # DB-backed CRM/order/billing/shipping
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic settings
│   │   │   ├── security.py           # JWT, bcrypt, RBAC
│   │   │   └── resilience.py         # ★ Retry, timeout, circuit breaker
│   │   ├── models/
│   │   │   ├── user.py               # User roles (customer/agent/manager/admin)
│   │   │   ├── ticket.py             # Ticket status machine
│   │   │   ├── message.py            # Chat messages (human + AI)
│   │   │   ├── order.py              # Orders + CustomerProfile
│   │   │   └── action_log.py         # Audit trail + approval requests
│   │   ├── routers/
│   │   │   ├── auth.py               # Login, register, /me
│   │   │   ├── tickets.py            # CRUD, assign, resolve
│   │   │   ├── chat.py               # Message send + agent trigger (30s timeout)
│   │   │   ├── approve.py            # Manager approval workflow
│   │   │   ├── admin.py              # User mgmt, stats, audit
│   │   │   ├── orders.py             # Order viewing
│   │   │   └── metrics.py            # ★ Evaluation metrics + circuit breaker health
│   │   ├── database.py               # Engine + session factory
│   │   └── main.py                   # App bootstrap
│   ├── seed.py                       # Demo data seeder
│   ├── requirements.txt              # Python dependencies

│   └── .env                          # Environment config
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx             # Auth + demo accounts
│   │   │   ├── Chat.jsx              # Customer chat portal
│   │   │   ├── AgentDashboard.jsx    # Agent ticket handler
│   │   │   ├── ManagerPortal.jsx     # Approvals + KPIs + ★ Evaluation Dashboard
│   │   │   └── AdminPanel.jsx        # System administration
│   │   ├── store/
│   │   │   ├── authStore.js          # Zustand auth state
│   │   │   └── ticketStore.js        # Zustand ticket/message state
│   │   ├── api/
│   │   │   └── client.js             # Axios + JWT interceptor
│   │   ├── App.jsx                   # Router + role-based protection
│   │   ├── index.css                 # Complete design system (670 lines)
│   │   └── main.jsx                  # React entry point
│   ├── index.html                    # HTML shell + SEO meta
│   ├── package.json                  # Node dependencies
│   └── vite.config.js                # Vite configuration

└── README.md                         # This file
```

---

## Security

- **JWT Authentication** — Tokens signed with HS256, configurable expiry
- **bcrypt Password Hashing** — Passwords never stored in plaintext
- **Role-Based Access Control (RBAC)** — Server-side enforcement via `require_roles()` decorators
- **Customer Data Isolation** — Customers can only access their own tickets and orders
- **CORS Configuration** — Whitelist-based origin control
- **SQL Injection Protection** — Parameterized queries via SQLAlchemy ORM
- **Circuit Breaker Protection** — Prevents LLM failure cascades from degrading the entire system

---

## License

This project is proprietary. All rights reserved.
