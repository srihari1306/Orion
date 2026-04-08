import asyncio
import json
import logging
import re
from langchain_groq import ChatGroq
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.resilience import with_retry, with_timeout, groq_breaker

logger = logging.getLogger("orion.decision")
settings = get_settings()

# Intents that mandate a verified order before any action
ORDER_REQUIRED_INTENTS = {"refund_request", "replacement_request", "wismo"}

# Only pass context fields relevant to the detected intent
INTENT_CONTEXT_FIELDS = {
    "refund_request":      ["customer_id", "tier", "lifetime_value", "abuse_score",
                            "prior_refund_in_30d", "refunds_last_30d", "order_status",
                            "order_amount", "order_id", "order_found", "order_id_provided",
                            "amount_mismatch"],
    "replacement_request": ["customer_id", "tier", "abuse_score", "order_status",
                            "order_amount", "order_id", "order_found", "order_id_provided",
                            "amount_mismatch", "shipping_delayed", "delay_reason"],
    "wismo":               ["customer_id", "tier", "order_status", "order_id",
                            "order_found", "order_id_provided",
                            "shipping_delayed", "delay_reason", "tracking_number"],
    "account_issue":       ["customer_id", "tier", "lifetime_value", "abuse_score", "churn_risk"],
    "bug_report":          ["customer_id", "tier"],
    "abuse":               ["customer_id", "abuse_score", "prior_refund_in_30d", "refunds_last_30d"],
    "general_inquiry":     ["customer_id", "tier"],
}

DECISION_PROMPT = """You are Orion's decision agent. Based ONLY on the triage and the relevant customer context provided, decide the resolution path.

TRIAGE:
- Intent: {intent}
- Sentiment: {sentiment_score}
- Urgency: {urgency}
- Entities: {entities}

RELEVANT CUSTOMER CONTEXT (only fields pertinent to this intent type):
{customer_context}

VALIDATION FLAGS:
- order_found: {order_found}
- order_id_provided: {order_id_provided}
- amount_mismatch: {amount_mismatch}

POLICY RULES — apply ONLY the rules relevant to the intent above:
- REFUND / REPLACEMENT:
  * If order_id_provided is false → NEED_INFO (ask customer for their order ID first)
  * If order_found is false → NEED_INFO (order not found, ask customer to verify)
  * If amount_mismatch is true → APPROVAL (amount discrepancy, needs human review)
  * AUTO-RESOLVE only if: amount < $75, not enterprise tier, abuse_score < 0.3, no prior_refund_in_30d, and order is found + verified
  * APPROVAL if amount >= $75 or enterprise tier
  * HANDOFF if abuse suspected (abuse_score >= 0.3)
- WISMO (where is my order):
  * If order_id_provided is false → NEED_INFO (ask customer for order ID)
  * If order_found is false → NEED_INFO
  * AUTO-RESOLVE if order and shipping data are available
  * HANDOFF if data is missing
- ACCOUNT ISSUE: always HANDOFF — account actions require human verification.
- BUG REPORT: always HANDOFF — requires engineering triage.
- GENERAL INQUIRY: AUTO-RESOLVE with an informational response.

Return ONLY valid JSON:
{{
  "resolution_path": "auto_resolve|approval|handoff|need_info",
  "confidence_score": <float 0.0-1.0>,
  "action_plan": {{
    "action_type": "refund|credit|replacement|reroute|closure|escalation|request_info",
    "amount": <float or null>,
    "order_id": "<string or null>",
    "reason": "<brief reason>",
    "missing_info": "<what info is needed from the customer, if need_info>"
  }},
  "briefing": "<concise briefing for human agent if handoff/approval — empty string otherwise>",
  "reasoning": "<one sentence explaining the decision>"
}}
"""


# Resilient LLM Call

@with_retry(max_attempts=3, backoff_seconds=1.5)
@groq_breaker.call
async def _call_decision_llm(prompt: str):
    """Call Groq with retry + circuit breaker protection."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
        max_tokens=800,
    )
    return await asyncio.to_thread(llm.invoke, prompt)


# Node Entry Point

def decision_node(state: AgentState) -> AgentState:
    intent = state.get("intent", "general_inquiry")
    order_found = state.get("order_found", False)
    order_id_provided = state.get("order_id_provided", False)
    amount_mismatch = state.get("amount_mismatch", False)
    steps = state.get("steps_taken", [])

    # ── HARD GUARDRAILS — override LLM for safety ────────────────────────
    # These checks run BEFORE the LLM to prevent hallucinated auto-resolves

    sentiment = float(state.get("sentiment_score", 0.0))
    # Only force a handoff if they are explicitly abusive, or if a "general_inquiry" is negative
    # (to prevent auto-resolving complaints). Refunds naturally have negative sentiment so we allow them to proceed.
    if intent == "abuse" or (intent == "general_inquiry" and sentiment <= -0.3):
        steps.append("decision: handoff (negative_sentiment_enforced)")
        return {
            **state,
            "resolution_path": "handoff",
            "confidence_score": 1.0,
            "action_plan": {
                "action_type": "escalation",
                "amount": None,
                "order_id": None,
                "reason": "Customer expressed strong anger/frustration",
            },
            "briefing": "Customer is highly dissatisfied or angry and requires immediate human handling.",
            "steps_taken": steps,
        }

    if intent in ORDER_REQUIRED_INTENTS:
        if not order_id_provided:
            steps.append("decision: need_info (order_id_not_provided)")
            return {
                **state,
                "resolution_path": "need_info",
                "confidence_score": 1.0,
                "action_plan": {
                    "action_type": "request_info",
                    "amount": None,
                    "order_id": None,
                    "reason": "Customer did not provide an order ID",
                    "missing_info": "order_id",
                },
                "briefing": "",
                "steps_taken": steps,
            }

        if not order_found:
            steps.append("decision: need_info (order_not_found)")
            return {
                **state,
                "resolution_path": "need_info",
                "confidence_score": 1.0,
                "action_plan": {
                    "action_type": "request_info",
                    "amount": None,
                    "order_id": state.get("entities", {}).get("order_id"),
                    "reason": "Order ID not found in our system",
                    "missing_info": "valid_order_id",
                },
                "briefing": "",
                "steps_taken": steps,
            }

    # ── LLM-based decision (with real validated context) ──────────────────

    # Filter customer context to only the fields relevant for this intent
    full_context = state.get("customer_context") or {}
    relevant_fields = INTENT_CONTEXT_FIELDS.get(intent, ["customer_id", "tier"])
    filtered_context = {k: v for k, v in full_context.items() if k in relevant_fields}

    prompt = DECISION_PROMPT.format(
        intent=intent,
        sentiment_score=state.get("sentiment_score", 0.0),
        urgency=state.get("urgency", "P2"),
        entities=json.dumps(state.get("entities") or {}, indent=2),
        customer_context=json.dumps(filtered_context, indent=2),
        order_found=order_found,
        order_id_provided=order_id_provided,
        amount_mismatch=amount_mismatch,
    )

    try:
        # Run the resilient async call from sync LangGraph context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        with_timeout(_call_decision_llm(prompt), seconds=12.0),
                    )
                    response = future.result()
            else:
                response = loop.run_until_complete(
                    with_timeout(_call_decision_llm(prompt), seconds=12.0)
                )
        except RuntimeError:
            response = asyncio.run(
                with_timeout(_call_decision_llm(prompt), seconds=12.0)
            )

        content = response.content.strip()

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1).strip()

        decision = json.loads(content)

        # ── POST-LLM SAFETY CHECKS ───────────────────────────────────────
        resolution = decision.get("resolution_path", "handoff")

        # Prevent auto-resolve if amount mismatch detected
        if amount_mismatch and resolution == "auto_resolve":
            resolution = "approval"
            decision["reasoning"] = (decision.get("reasoning", "") +
                " [OVERRIDDEN: amount mismatch detected — escalated to approval]")

        # Prevent auto-resolve on high-value orders (>= $75) regardless of LLM decision
        customer_context = state.get("customer_context") or {}
        order_amount = customer_context.get("order_amount", 0)
        if (intent in {"refund_request", "replacement_request"}
            and resolution == "auto_resolve"
            and order_amount is not None
            and order_amount >= 75):
            resolution = "approval"
            decision["reasoning"] = (decision.get("reasoning", "") +
                f" [OVERRIDDEN: order amount ${order_amount:.2f} >= $75 threshold — requires approval]")

        steps.append(f"decision: {resolution}")

        return {
            **state,
            "resolution_path": resolution,
            "confidence_score": decision.get("confidence_score", 0.5),
            "action_plan": decision.get("action_plan", {}),
            "briefing": decision.get("briefing", ""),
            "steps_taken": steps,
        }

    except Exception as e:
        # ── FALLBACK: safe handoff to human ──────────────────────────────
        logger.warning(f"[Decision] LLM failed, falling back to handoff: {e}")
        steps.append(f"decision_error: {str(e)}")
        steps.append("decision_fallback_used")
        return {
            **state,
            "resolution_path": "handoff",
            "confidence_score": 0.3,
            "action_plan": {
                "action_type": "escalation",
                "reason": "Decision engine unavailable — auto-escalated to human agent",
            },
            "briefing": f"Decision engine error (auto-escalated): {str(e)}",
            "error": f"Decision failed: {str(e)}",
            "steps_taken": steps,
        }
