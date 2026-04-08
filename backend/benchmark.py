import time
import sys
import os
import json
import statistics

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.database import create_all_tables
from app.models.ticket import Ticket, TicketStatus
from app.models.message import Message
from app.models.user import User

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def get_customer():
    db = SessionLocal()
    customer = db.query(User).filter(User.email == "customer@demo.com").first()
    db.close()
    return customer

def measure_pipeline(ticket_id, customer_id, raw_text, linked_order_id=None):
    from app.agents.graph import run_orion

    start = time.time()
    result = run_orion(
        ticket_id=ticket_id,
        customer_id=customer_id,
        raw_text=raw_text,
        channel="benchmark",
        prior_context=None,
        linked_order_id=linked_order_id,
    )
    end = time.time()

    elapsed = round(end - start, 2)
    return {
        "elapsed_seconds": elapsed,
        "intent": result.get("intent"),
        "resolution_path": result.get("resolution_path"),
        "confidence_score": result.get("confidence_score"),
        "steps_taken": result.get("steps_taken", []),
        "error": result.get("error"),
        "has_reply": bool(result.get("reply_text")),
    }

def run_benchmark():
    print("=" * 70)
    print("ORION PERFORMANCE BENCHMARK")
    print("=" * 70)

    customer = get_customer()
    if not customer:
        print("No customer found. Run seed.py first.")
        return

    customer_id = customer.id
    print(f"\nUsing customer: {customer.name} (id={customer_id})")

    test_cases = [
        {
            "name": "Refund with order (auto-resolve path)",
            "text": "I received defective headphones from order ORD-1001 and want a full refund of $49.99",
            "order_id": "ORD-1001",
        },
        {
            "name": "High-value refund (approval path)",
            "text": "The premium laptop stand from ORD-1003 arrived cracked, I need a refund for $179.99",
            "order_id": "ORD-1003",
        },
        {
            "name": "Shipping inquiry (WISMO)",
            "text": "Where is my mechanical keyboard? Order ORD-1004, it says shipped but hasn't arrived",
            "order_id": "ORD-1004",
        },
        {
            "name": "No order ID (need_info path)",
            "text": "I want a refund for a broken product I received last week",
            "order_id": None,
        },
        {
            "name": "General inquiry (informational)",
            "text": "What is your return policy? How long do refunds take to process?",
            "order_id": None,
        },
    ]

    results = []
    node_times = {"triage": [], "context": [], "decision": [], "reply": []}

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"  Test {i}/{len(test_cases)}: {tc['name']}")
        print(f"  Input: \"{tc['text'][:70]}...\"")
        print(f"{'─' * 60}")

        db = SessionLocal()
        ticket = Ticket(
            customer_id=customer_id,
            subject=f"Benchmark Test {i}",
            status=TicketStatus.open,
            order_id=tc.get("order_id"),
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id
        db.close()

        try:
            result = measure_pipeline(
                ticket_id=ticket_id,
                customer_id=customer_id,
                raw_text=tc["text"],
                linked_order_id=tc.get("order_id"),
            )
            results.append({**result, "test_name": tc["name"]})

            elapsed = result["elapsed_seconds"]
            intent = result.get("intent", "?")
            path = result.get("resolution_path", "?")
            conf = result.get("confidence_score", 0)
            steps = result.get("steps_taken", [])

            print(f"   Time:       {elapsed}s")
            print(f"   Intent:     {intent}")
            print(f"  Path:       {path}")
            print(f"  Confidence: {conf}")
            print(f"  Steps:      {' → '.join(steps)}")
            print(f"  Has reply:  {'' if result['has_reply'] else ''}")

            if result.get("error"):
                print(f"   Error:      {result['error']}")

            fallback_used = any("fallback" in s for s in steps)
            if fallback_used:
                print(f"   FALLBACK TRIGGERED")

        except Exception as e:
            print(f"  PIPELINE ERROR: {e}")
            results.append({"elapsed_seconds": 0, "error": str(e), "test_name": tc["name"]})

    print("\n" + "=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)

    successful = [r for r in results if not r.get("error")]
    times = [r["elapsed_seconds"] for r in successful]

    if times:
        avg_time = round(statistics.mean(times), 2)
        median_time = round(statistics.median(times), 2)
        min_time = round(min(times), 2)
        max_time = round(max(times), 2)
        p95_time = round(sorted(times)[int(len(times) * 0.95)], 2) if len(times) > 1 else times[0]
    else:
        avg_time = median_time = min_time = max_time = p95_time = 0

    paths = {}
    intents = {}
    confidences = []
    fallback_count = 0

    for r in successful:
        p = r.get("resolution_path", "unknown")
        paths[p] = paths.get(p, 0) + 1
        i = r.get("intent", "unknown")
        intents[i] = intents.get(i, 0) + 1
        if r.get("confidence_score"):
            confidences.append(float(r["confidence_score"]))
        if any("fallback" in s for s in r.get("steps_taken", [])):
            fallback_count += 1

    auto_resolve_count = paths.get("auto_resolve", 0)
    total = len(successful)
    auto_resolve_rate = round(auto_resolve_count / total * 100, 1) if total else 0
    escalation_rate = round((paths.get("handoff", 0) + paths.get("approval", 0)) / total * 100, 1) if total else 0
    avg_confidence = round(statistics.mean(confidences), 3) if confidences else 0

    print(f"\n  PERFORMANCE METRICS")
    print(f"  {'─' * 50}")
    print(f"  Tickets processed:        {total}")
    print(f"  Avg resolution time:      {avg_time}s")
    print(f"  Median resolution time:   {median_time}s")
    print(f"  Min resolution time:      {min_time}s")
    print(f"  Max resolution time:      {max_time}s")
    print(f"  P95 resolution time:      {p95_time}s")

    print(f"\n  RESOLUTION METRICS")
    print(f"  {'─' * 50}")
    print(f"  Auto-resolve rate:        {auto_resolve_rate}%")
    print(f"  Escalation rate:          {escalation_rate}%")
    print(f"  Avg LLM confidence:       {avg_confidence}")
    print(f"  Fallback triggers:        {fallback_count}/{total}")

    print(f"\n  RESOLUTION PATH DISTRIBUTION")
    print(f"  {'─' * 50}")
    for p, c in sorted(paths.items(), key=lambda x: -x[1]):
        pct = round(c / total * 100, 1)
        print(f"  {p:20s}: {c} ({pct}%)")

    print(f"\n   INTENT DISTRIBUTION")
    print(f"  {'─' * 50}")
    for i, c in sorted(intents.items(), key=lambda x: -x[1]):
        print(f"  {i:20s}: {c}")

    print(f"\n   PER-TEST TIMINGS")
    print(f"  {'─' * 50}")
    for r in results:
        status = "" if not r.get("error") else ""
        print(f"  {status} {r.get('test_name', '?'):45s} {r.get('elapsed_seconds', 0):>6.2f}s  → {r.get('resolution_path', 'error')}")

    return {
        "performance": {
            "total_tickets_processed": total,
            "avg_resolution_time_seconds": avg_time,
            "median_resolution_time_seconds": median_time,
            "min_resolution_time_seconds": min_time,
            "max_resolution_time_seconds": max_time,
            "p95_resolution_time_seconds": p95_time,
        },
        "resolution": {
            "auto_resolve_rate_pct": auto_resolve_rate,
            "escalation_rate_pct": escalation_rate,
            "avg_confidence_score": avg_confidence,
            "fallback_trigger_count": fallback_count,
            "path_distribution": paths,
        },
        "intents": intents,
        "per_test": [
            {
                "name": r.get("test_name"),
                "time_seconds": r.get("elapsed_seconds"),
                "intent": r.get("intent"),
                "path": r.get("resolution_path"),
                "confidence": r.get("confidence_score"),
                "steps": r.get("steps_taken"),
                "has_reply": r.get("has_reply"),
            }
            for r in results
        ],
    }

if __name__ == "__main__":
    data = run_benchmark()
    if data:
        with open("benchmark_results.json", "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nRaw data saved to benchmark_results.json")
