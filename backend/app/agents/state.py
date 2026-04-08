from typing import TypedDict, Optional

class AgentState(TypedDict):
    ticket_id: int
    customer_id: int
    raw_text: str
    channel: str
    prior_context: Optional[str]  # from memory/re-opens
    linked_order_id: Optional[str]

    intent: Optional[str]
    sentiment_score: Optional[float]
    urgency: Optional[str]
    entities: Optional[dict]

    crm_data: Optional[dict]
    order_data: Optional[dict]
    billing_data: Optional[dict]
    shipping_data: Optional[dict]
    customer_context: Optional[dict]  # merged

    order_found: Optional[bool]          # was a matching order located?
    order_id_provided: Optional[bool]    # did the customer supply an order ID?
    amount_mismatch: Optional[bool]      # does claimed amount differ from actual?

    confidence_score: Optional[float]
    resolution_path: Optional[str]  # "auto_resolve" | "approval" | "handoff" | "need_info"
    action_plan: Optional[dict]
    briefing: Optional[str]

    action_result: Optional[dict]
    reply_text: Optional[str]

    error: Optional[str]
    steps_taken: list[str]
