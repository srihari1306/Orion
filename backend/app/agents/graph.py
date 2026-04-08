from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes.triage_node import triage_node
from app.agents.nodes.context_node import context_node
from app.agents.nodes.decision_node import decision_node
from app.agents.nodes.action_node import action_node
from app.agents.nodes.reply_node import reply_node

def route_after_decision(state: AgentState) -> str:
    return "action"

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("triage", triage_node)
    graph.add_node("context", context_node)
    graph.add_node("decision", decision_node)
    graph.add_node("action", action_node)
    graph.add_node("reply", reply_node)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "context")
    graph.add_edge("context", "decision")
    graph.add_conditional_edges("decision", route_after_decision, {"action": "action"})
    graph.add_edge("action", "reply")
    graph.add_edge("reply", END)

    return graph.compile()

orion_graph = build_graph()

def run_orion(
    ticket_id: int,
    customer_id: int,
    raw_text: str,
    channel: str = "chat",
    prior_context: str = None,
    linked_order_id: str = None,
) -> AgentState:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "raw_text": raw_text,
        "channel": channel,
        "prior_context": prior_context,
        "linked_order_id": linked_order_id,
        "intent": None,
        "sentiment_score": None,
        "urgency": None,
        "entities": None,
        "crm_data": None,
        "order_data": None,
        "billing_data": None,
        "shipping_data": None,
        "customer_context": None,
        "order_found": None,
        "order_id_provided": None,
        "amount_mismatch": None,
        "confidence_score": None,
        "resolution_path": None,
        "action_plan": None,
        "briefing": None,
        "action_result": None,
        "reply_text": None,
        "error": None,
        "steps_taken": [],
    }

    return orion_graph.invoke(initial_state)

