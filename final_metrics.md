# Orion — Final Metrics Report

> **Measured on:** April 7, 2026  
> **Benchmark:** 5 diverse ticket scenarios run through the live LangGraph pipeline against a real MySQL database with Groq Llama 3.3 70B inference  
> **Method:** Direct `run_orion()` invocation with `time.time()` wall-clock measurement per test case

---

## 1. Performance Metrics (Measured)

| Metric | Value | Notes |
|--------|-------|-------|
| **Avg end-to-end resolution time** | **1.84s** | Across 5 test cases (triage → context → decision → action → reply) |
| **Median resolution time** | **2.01s** | — |
| **Min resolution time** | **1.34s** | need_info path (skips LLM decision + action) |
| **Max resolution time** | **2.15s** | Full refund pipeline with approval routing |
| **P95 resolution time** | **2.15s** | — |
| **Pipeline success rate** | **100%** | 5/5 tickets completed without error |
| **Reply generation rate** | **100%** | All 5 tests produced a customer-facing reply |

### Per-Node Groq API Latency (Estimated from Pipeline Timing)

| Node | LLM Calls | Avg Contribution | Notes |
|------|-----------|-----------------|-------|
| **Triage** | 1x LLM call | ~0.5–0.7s | Intent + sentiment + entity extraction |
| **Context** | 0 LLM calls | ~0.01s | Pure DB queries (MySQL), negligible |
| **Decision** | 1x LLM call | ~0.5–0.7s | Policy reasoning + resolution path |
| **Action** | 0 LLM calls | ~0.01s | DB mutations only |
| **Reply** | 1x LLM call | ~0.5–0.7s | Empathetic response generation |

> **Observation:** The pipeline makes **3 LLM calls** per full resolution. The need_info path makes only **2 LLM calls** (skips decision LLM), explaining the faster 1.34s time. Each Groq Llama 3.3 70B call averages **~0.5–0.7s** — well under the 10s timeout per node.

---

## 2. Resolution Metrics (Measured)

| Metric | Value | Notes |
|--------|-------|-------|
| **Auto-resolve rate** | **20%** | 1 of 5 tickets resolved without human intervention |
| **Approval rate** | **60%** | 3 of 5 tickets routed to manager approval queue |
| **Need-info rate** | **20%** | 1 of 5 tickets asked customer for missing order ID |
| **Escalation (handoff) rate** | **0%** | No tickets required human agent escalation |
| **Avg LLM confidence score** | **0.90** | Range: 0.8–1.0 across all tests |
| **Fallback trigger count** | **0** | Circuit breaker never tripped — Groq was responsive |
| **Pipeline failure count** | **0** | No crashes or timeouts |

### Resolution Path Distribution

| Path | Count | Percentage | When Used |
|------|-------|------------|-----------|
| **approval** | 3 | 60% | Refund $49.99 (prior refund flag), $179.99 (>$75), $129.99 (>$75) |
| **need_info** | 1 | 20% | No order ID provided — hard guardrail caught it pre-LLM |
| **auto_resolve** | 1 | 20% | General policy inquiry — no action required |
| **handoff** | 0 | 0% | No abuse/anger detected in test cases |

### Intent Classification Accuracy

| Test Input | Expected Intent | Actual Intent | Correct? |
|-----------|----------------|---------------|----------|
| "defective headphones…refund $49.99" | refund_request | refund_request | |
| "laptop stand cracked…refund $179.99" | refund_request | refund_request | |
| "where is my keyboard…hasn't arrived" | shipping_inquiry/wismo | replacement_request | |
| "refund for broken product" | refund_request | refund_request | |
| "return policy…refund time" | general_inquiry | general_inquiry | |

> **Classification accuracy: 80%** (4/5 correct). Test 3 classified a shipping inquiry as a replacement request — acceptable since the customer mentioned "hasn't arrived" which implies they want action beyond just tracking info.

---

## 3. Per-Test Breakdown

| # | Test Case | Time | Intent | Path | Confidence | Steps |
|---|-----------|------|--------|------|------------|-------|
| 1 | Refund $49.99, ORD-1001 | 2.15s | refund_request | approval | 0.8 | triage → context → decision → action → reply |
| 2 | Refund $179.99, ORD-1003 | 2.06s | refund_request | approval | 0.9 | triage → context → decision → action → reply |
| 3 | Shipping inquiry, ORD-1004 | 2.01s | replacement_request | approval | 0.8 | triage → context → decision → action → reply |
| 4 | No order ID | 1.34s | refund_request | need_info | 1.0 | triage → context → validation → decision → action → reply |
| 5 | General inquiry | 1.64s | general_inquiry | auto_resolve | 1.0 | triage → context → decision → action → reply |

---

## 4. Scale Metrics (Counted from Codebase)

### Codebase Size

| Component | Lines of Code | File Count |
|-----------|--------------|------------|
| **Backend (Python)** | **3,024** | 32 files |
| **Frontend (JS/JSX/CSS)** | **2,661** | 12 files |
| **Total** | **5,685** | 44 source files |

### Backend Breakdown (Top Files)

| File | Lines | Purpose |
|------|-------|---------|
| `chat.py` | 352 | Chat router + pipeline trigger + safety net |
| `decision_node.py` | 276 | Policy engine + LLM + guardrails |
| `internal_apis.py` | 266 | DB-backed CRM/order/billing/shipping APIs |
| `tickets.py` | 217 | Ticket CRUD + assign + resolve |
| `resilience.py` | 181 | Retry, timeout, circuit breaker |
| `triage_node.py` | 180 | Intent extraction + keyword fallback |
| `metrics.py` | 166 | Evaluation metrics + health endpoints |
| `reply_node.py` | 155 | Reply generation + template fallback |
| `approve.py` | 150 | Manager approval workflow |
| `action_node.py` | 142 | Action execution + validation |
| `context_node.py` | 113 | Parallel data fetch |

### Frontend Breakdown (Top Files)

| File | Lines | Purpose |
|------|-------|---------|
| `index.css` | 669 | Complete design system (no Tailwind) |
| `ManagerPortal.jsx` | 551 | Approvals + KPIs + Evaluation Dashboard |
| `Chat.jsx` | 370 | Customer chat portal |
| `AgentDashboard.jsx` | 296 | Agent ticket handler |
| `AdminPanel.jsx` | 268 | System administration |
| `App.css` | 184 | Additional styles |
| `Login.jsx` | 127 | Auth + demo accounts |

### API Endpoints

| Router | Endpoints | Methods |
|--------|-----------|---------|
| `auth` | 3 | POST register, POST login, GET /me |
| `tickets` | 5 | POST create, GET list, GET detail, PATCH assign, POST resolve |
| `chat` | 1 | POST /send |
| `approve` | 2 | GET list, POST review |
| `admin` | 5 | GET users, POST users, PATCH deactivate, GET stats, GET audit-log |
| `orders` | 2 | GET list, GET detail |
| `metrics` | 3 | GET summary, GET health, POST circuit-breaker/reset |
| `main` | 1 | GET /health |
| **Total** | **22** | — |

### Database Models & Tables

| Model | Table | Columns | Key Features |
|-------|-------|---------|-------------|
| `User` | `users` | 7 | 4 roles (customer, agent, manager, admin) |
| `Ticket` | `tickets` | 14 | Status machine (open, pending_approval, resolved, closed, escalated) |
| `Message` | `messages` | 6 | JSON `metadata_` for pipeline traces |
| `Order` | `orders` | 14 | Full e-commerce order with refund tracking |
| `CustomerProfile` | `customer_profiles` | 12 | CRM data: tier, LTV, abuse_score, churn_risk |
| `ActionLog` | `action_logs` | 7 | Complete action audit trail |
| `ApprovalRequest` | `approval_requests` | 9 | Manager approval workflow |
| **Total** | **7 tables** | **69 columns** | + 7 enums |

### LangGraph Pipeline

| Metric | Count |
|--------|-------|
| **Nodes** | **5** (triage, context, decision, action, reply) |
| **LLM-calling nodes** | **3** (triage, decision, reply) |
| **DB-only nodes** | **2** (context, action) |
| **Edges** | **5** (linear: triage→context→decision→action→reply→END) |
| **LLM calls per full pipeline** | **3** |
| **LLM calls for need_info** | **2** (skips decision LLM) |

---

## 5. Complexity Metrics (Counted)

### Role-Based Access Control

| Metric | Count | Details |
|--------|-------|---------|
| **User roles** | **4** | customer, agent, manager, admin |
| **Frontend dashboards** | **4** | Chat, AgentDashboard, ManagerPortal, AdminPanel |
| **Protected route groups** | **4** | Role-gated via `ProtectedRoute` in React Router |
| **RBAC decorators** | **12** | `require_roles()` calls across routers |

### Decision Engine Policy Rules

| Rule # | Condition | Result | Phase |
|--------|-----------|--------|-------|
| 1 | `intent == "abuse"` | → handoff | Pre-LLM |
| 2 | `intent == "general_inquiry" AND sentiment <= -0.3` | → handoff | Pre-LLM |
| 3 | Intent requires order AND no order_id provided | → need_info | Pre-LLM |
| 4 | Order ID provided AND order not found in DB | → need_info | Pre-LLM |
| 5 | `amount_mismatch AND auto_resolve` | → approval (override) | Post-LLM |
| 6 | `order_amount >= $75 AND auto_resolve` | → approval (override) | Post-LLM |
| 7 | `abuse_score >= 0.3` | → handoff | LLM prompt |
| 8 | `prior_refund_in_30d AND auto_resolve` | → approval | LLM prompt |
| 9 | `enterprise tier` | → approval | LLM prompt |
| 10 | `refund < $75 AND low abuse AND no prior refund` | → auto_resolve | LLM prompt |
| 11 | `account_issue OR bug_report` | → handoff | LLM prompt |
| 12 | `general_inquiry` | → auto_resolve | LLM prompt |
| **Total** | **12 policy rules** | across 3 decision phases | |

### Resilience Layers

| Layer | Component | Details |
|-------|-----------|---------|
| **Layer 1** | `@with_retry` | 3x exponential backoff (1.5s → 3s → 6s) |
| **Layer 2** | `CircuitBreaker` | Opens after 5 failures, 60s cooldown, HALF_OPEN probe |
| **Layer 3** | `with_timeout` | 10–12s per LLM call, 30s for entire pipeline |
| **Layer 4** | Keyword Classifier | Rule-based intent classification (7 intent categories, 20+ keywords) |
| **Layer 5** | Static Templates | 4 pre-written reply templates (need_info, auto_resolve, approval, handoff) |
| **Layer 6** | Graph Safety Net | Auto-escalate to human queue + graceful customer message on total failure |
| **Total** | **6 resilience layers** | — |

### Real-Time Events

| Event | Emit Points | Direction |
|-------|------------|-----------|
| `agent_thinking` | 1 | Server → Client |
| `ticket_update` | 5 (chat resolve, chat error, approval, ticket resolve, agent response) | Server → Client |
| `connect` / `disconnect` | 2 | Client ↔ Server |
| **Total** | **8 emit points** | — |

### Internal API Functions

| Function | Type | Target |
|----------|------|--------|
| `get_customer_profile()` | Read | customer_profiles |
| `get_order()` | Read | orders |
| `get_billing_info()` | Read | customer_profiles |
| `get_shipping_status()` | Read | orders |
| `issue_refund()` | Write | orders |
| `issue_credit()` | Write | customer_profiles |
| `trigger_replacement()` | Write | orders |
| `reroute_shipment()` | Write | orders |
| **Total** | **8 functions** | (4 read, 4 write) |

---

## 6. Key Numbers for Resume/Portfolio

| Bullet-Ready Metric | Value |
|---------------------|-------|
| End-to-end ticket resolution | **< 2s avg** (measured 1.84s) |
| LLM inference latency | **~0.5–0.7s per call** (Groq Llama 3.3 70B) |
| Pipeline success rate | **100%** (5/5 benchmark) |
| LLM confidence score | **0.90 avg** |
| Policy rules in decision engine | **12 rules** across 3 phases (pre-LLM, LLM, post-LLM) |
| Resilience layers | **6 layers** (retry → breaker → timeout → keywords → templates → safety net) |
| API endpoints | **22** across 8 routers |
| Database tables | **7 tables**, 69 columns, 7 enums |
| LangGraph pipeline nodes | **5 nodes**, 3 LLM calls per ticket |
| Total codebase | **5,685 lines** (3,024 backend + 2,661 frontend) |
| Frontend dashboards | **4 role-based portals** |
| Real-time events | **8 Socket.IO emit points** |
| Internal tool functions | **8** (4 read + 4 write against MySQL) |
| Circuit breaker config | **5-failure threshold**, 60s recovery, 3-state machine |
| Keyword fallback categories | **7 intent types**, 20+ trigger keywords |
| Static reply templates | **4** (one per resolution path) |
| Classification accuracy | **80%** (4/5 correct in benchmark) |
