import asyncio
import json
import logging
import re
from langchain_groq import ChatGroq
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.resilience import with_retry, with_timeout, groq_breaker

logger = logging.getLogger("orion.triage")
settings = get_settings()

TRIAGE_PROMPT = """You are Orion's triage agent. Parse the customer's LATEST message below and return a JSON object ONLY.

Customer's Latest Message: {raw_text}
Channel: {channel}
Prior context (AI's previous messages): {prior_context}

IMPORTANT: If the user's latest message contains an order ID (like ORD-1001), you MUST extract it into the 'order_id' entity field.

Return ONLY valid JSON with these exact keys:
{{
  "intent": "refund_request|wismo|account_issue|bug_report|abuse|replacement_request|general_inquiry",
  "sentiment_score": <float -1.0 to 1.0>,
  "urgency": "P0|P1|P2|P3",
  "entities": {{
    "order_id": "<string or null>",
    "product_name": "<string or null>",
    "amount": <float or null>,
    "dates": [],
    "customer_complaint": "<brief summary>"
  }}
}}

P0 = immediate (system outage, fraud), P1 = high (refund >$100, delivery failed), P2 = medium, P3 = low.
"""


# Keyword Fallback Classifier — used when LLM is unreachable

KEYWORD_FALLBACKS = {
    "refund_request":       ["refund", "money back", "charge", "reimburse", "charged", "overcharged"],
    "wismo":                ["shipping", "tracking", "delivery", "where is", "shipped", "where's my order"],
    "replacement_request":  ["replacement", "replace", "exchange", "swap"],
    "account_issue":        ["account", "login", "password", "locked", "cannot access"],
    "bug_report":           ["bug", "error", "crash", "broken feature", "glitch"],
    "abuse":                ["scam", "fraud", "stolen"],
    "general_inquiry":      [],  # catch-all
}


def keyword_classify(text: str) -> str:
    """Simple keyword-based intent classifier — production fallback."""
    text_lower = text.lower()
    for intent, keywords in KEYWORD_FALLBACKS.items():
        if any(k in text_lower for k in keywords):
            return intent
    return "general_inquiry"


def keyword_urgency(intent: str) -> str:
    """Estimate urgency from intent alone."""
    urgent = {"abuse": "P0", "refund_request": "P1", "replacement_request": "P1"}
    return urgent.get(intent, "P2")


# Resilient LLM Call

@with_retry(max_attempts=3, backoff_seconds=1.5)
@groq_breaker.call
async def _call_triage_llm(prompt: str):
    """Call Groq with retry + circuit breaker protection."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
        max_tokens=512,
    )
    return await asyncio.to_thread(llm.invoke, prompt)


# Node Entry Point

def triage_node(state: AgentState) -> AgentState:
    prompt = TRIAGE_PROMPT.format(
        raw_text=state["raw_text"],
        channel=state.get("channel", "unknown"),
        prior_context=state.get("prior_context") or "None",
    )

    steps = state.get("steps_taken", [])

    try:
        # Run the resilient async call from sync LangGraph context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        with_timeout(_call_triage_llm(prompt), seconds=10.0),
                    )
                    response = future.result()
            else:
                response = loop.run_until_complete(
                    with_timeout(_call_triage_llm(prompt), seconds=10.0)
                )
        except RuntimeError:
            response = asyncio.run(
                with_timeout(_call_triage_llm(prompt), seconds=10.0)
            )

        content = response.content.strip()

        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1).strip()

        triage = json.loads(content)

        # Regex fallback: if LLM missed it but raw text has an ORD- format, grab it
        if not triage.get("entities", {}).get("order_id"):
            fallback_match = re.search(r"(ORD-\d+)", state["raw_text"], re.IGNORECASE)
            if fallback_match:
                if "entities" not in triage:
                    triage["entities"] = {}
                triage["entities"]["order_id"] = fallback_match.group(1).upper()

        steps.append("triage_complete")

        return {
            **state,
            "intent": triage.get("intent", "general_inquiry"),
            "sentiment_score": triage.get("sentiment_score", 0.0),
            "urgency": triage.get("urgency", "P2"),
            "entities": triage.get("entities", {}),
            "steps_taken": steps,
        }

    except Exception as e:
        # ── FALLBACK: keyword classifier ─────────────────────────────────
        logger.warning(f"[Triage] LLM failed entirely, using keyword fallback: {e}")
        fallback_intent = keyword_classify(state["raw_text"])
        fallback_urgency = keyword_urgency(fallback_intent)

        # Try to extract order ID from text even without LLM
        entities = {}
        oid_match = re.search(r"(ORD-\d+)", state["raw_text"], re.IGNORECASE)
        if oid_match:
            entities["order_id"] = oid_match.group(1).upper()

        steps.append(f"triage_error: {str(e)}")
        steps.append("triage_fallback_used")

        return {
            **state,
            "intent": fallback_intent,
            "sentiment_score": 0.0,
            "urgency": fallback_urgency,
            "entities": entities,
            "confidence_score": 0.4,  # Low confidence flag for metrics
            "error": f"Triage LLM failed (fallback used): {str(e)}",
            "steps_taken": steps,
        }
