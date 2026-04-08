import asyncio
import logging
import re
from langchain_groq import ChatGroq
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.resilience import with_retry, with_timeout, groq_breaker

logger = logging.getLogger("orion.reply")
settings = get_settings()

REPLY_PROMPT = """You are Orion, an empathetic AI customer support agent for a modern e-commerce platform.

Write a professional, warm, and concise reply to the customer based on the context below.

CUSTOMER MESSAGE: {raw_text}
INTENT: {intent}
SENTIMENT: {sentiment_score}
RESOLUTION PATH: {resolution_path}
ACTION TAKEN: {action_result}
CUSTOMER CONTEXT: {customer_context}
BRIEFING (if handoff): {briefing}

Guidelines:
- Be warm, clear, and concise (3-5 sentences)
- If auto-resolved: confirm the action taken and give the customer next steps.
- If it's an informational check (like WISMO), provide the specific status update (e.g. shipping delays, reasons) using the CUSTOMER CONTEXT.
- NEVER use internal AI or system terminology like "closure action", "auto-resolve", or "handoff". Translate system actions into human-friendly explanations.
- If pending approval: tell customer their case is under review and they'll hear back shortly
- If handoff: acknowledge frustration, confirm a human specialist will take over shortly
- If need_info: kindly ask the customer for the specific missing information (order ID, etc.), explain WHY you need it, and assure them you'll help once they provide it
- Never say "AI" or "bot" — speak as Orion support team
- End with a helpful closing line

Reply:"""

FALLBACK_REPLIES = {
    "need_info": (
        "Thank you for reaching out! To assist you with your request, "
        "we'll need {missing_info}. You can find this in your order confirmation email "
        "(it starts with ORD-). Once you share that, we'll get this resolved right away!"
    ),
    "auto_resolve": (
        "We've taken care of your request! The action has been processed and you should "
        "see updates reflected shortly. If you have any other questions, don't hesitate to ask."
    ),
    "approval": (
        "Thank you for your patience. Your request is currently under review by our team. "
        "We'll follow up with you shortly once the review is complete."
    ),
    "handoff": (
        "We hear you, and we want to make sure this is handled with the care it deserves. "
        "A specialist from our team will be reaching out to you shortly. Thank you for your patience."
    ),
}

def _get_fallback_reply(resolution_path: str, action_result: dict) -> str:
    template = FALLBACK_REPLIES.get(resolution_path, FALLBACK_REPLIES["handoff"])
    if resolution_path == "need_info":
        missing = action_result.get("missing_info", "your order ID")
        return template.format(missing_info=missing)
    return template

@with_retry(max_attempts=3, backoff_seconds=1.5)
@groq_breaker.call
async def _call_reply_llm(prompt: str):
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        temperature=0.4,
        max_tokens=400,
    )
    return await asyncio.to_thread(llm.invoke, prompt)

def reply_node(state: AgentState) -> AgentState:
    resolution_path = state.get("resolution_path", "handoff")
    action_result = state.get("action_result") or {}

    prompt = REPLY_PROMPT.format(
        raw_text=state.get("raw_text", ""),
        intent=state.get("intent", "general_inquiry"),
        sentiment_score=state.get("sentiment_score", 0.0),
        resolution_path=resolution_path,
        action_result=action_result or "No action taken",
        customer_context=state.get("customer_context") or "N/A",
        briefing=state.get("briefing") or "N/A",
    )

    steps = state.get("steps_taken", [])

    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        with_timeout(_call_reply_llm(prompt), seconds=10.0),
                    )
                    response = future.result()
            else:
                response = loop.run_until_complete(
                    with_timeout(_call_reply_llm(prompt), seconds=10.0)
                )
        except RuntimeError:
            response = asyncio.run(
                with_timeout(_call_reply_llm(prompt), seconds=10.0)
            )

        reply_text = response.content.strip()
        steps.append("reply_drafted")

        return {**state, "reply_text": reply_text, "steps_taken": steps}

    except Exception as e:
        logger.warning(f"[Reply] LLM failed, using static fallback: {e}")
        fallback = _get_fallback_reply(resolution_path, action_result)
        steps.append(f"reply_error: {str(e)}")
        steps.append("reply_fallback_used")
        return {
            **state,
            "reply_text": fallback,
            "error": f"Reply generation failed (fallback used): {str(e)}",
            "steps_taken": steps,
        }
