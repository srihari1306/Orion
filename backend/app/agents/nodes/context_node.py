import asyncio
from app.agents.state import AgentState
from app.agents.tools.internal_apis import fetch_all_context

ORDER_REQUIRED_INTENTS = {"refund_request", "replacement_request", "wismo"}

def context_node(state: AgentState) -> AgentState:
    customer_id = state["customer_id"]
    entities = state.get("entities") or {}
    intent = state.get("intent", "general_inquiry")

    linked_order_id = state.get("linked_order_id")
    triage_order_id = entities.get("order_id")
    order_id = linked_order_id or triage_order_id

    order_id_provided = order_id is not None and order_id != "" and order_id != "null" and order_id != "None"

    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, fetch_all_context(customer_id, order_id))
                    raw_context = future.result()
            else:
                raw_context = loop.run_until_complete(fetch_all_context(customer_id, order_id))
        except RuntimeError:
            raw_context = asyncio.run(fetch_all_context(customer_id, order_id))

        order_found = raw_context["order"].get("found", False)

        amount_mismatch = False
        claimed_amount = entities.get("amount")
        if order_found and claimed_amount is not None:
            try:
                actual = raw_context["order"]["total_amount"]
                claimed = float(claimed_amount)
                if abs(actual - claimed) > 1.0:
                    amount_mismatch = True
            except (TypeError, ValueError):
                pass

        customer_context = {
            "customer_id": customer_id,
            "tier": raw_context["crm"]["tier"],
            "lifetime_value": raw_context["crm"]["lifetime_value"],
            "churn_risk": raw_context["crm"]["churn_risk"],
            "abuse_score": raw_context["billing"]["abuse_score"],
            "prior_refund_in_30d": raw_context["billing"]["prior_refund_in_30d"],
            "refunds_last_30d": raw_context["billing"]["refunds_last_30_days"],
            "order_status": raw_context["order"]["status"],
            "order_amount": raw_context["order"]["total_amount"],
            "order_id": raw_context["order"]["order_id"],
            "order_found": order_found,
            "order_id_provided": order_id_provided,
            "amount_mismatch": amount_mismatch,
            "shipping_delayed": raw_context["shipping"]["is_delayed"],
            "delay_reason": raw_context["shipping"]["delay_reason"],
            "tracking_number": raw_context["shipping"]["tracking_number"],
        }

        steps = state.get("steps_taken", [])
        steps.append("context_fetched")

        if intent in ORDER_REQUIRED_INTENTS:
            if not order_id_provided:
                steps.append("validation: order_id_not_provided")
            if not order_found:
                steps.append("validation: order_not_found")
            if amount_mismatch:
                steps.append("validation: amount_mismatch")

        return {
            **state,
            "crm_data": raw_context["crm"],
            "order_data": raw_context["order"],
            "billing_data": raw_context["billing"],
            "shipping_data": raw_context["shipping"],
            "customer_context": customer_context,
            "order_found": order_found,
            "order_id_provided": order_id_provided,
            "amount_mismatch": amount_mismatch,
            "steps_taken": steps,
        }

    except Exception as e:
        steps = state.get("steps_taken", [])
        steps.append(f"context_error: {str(e)}")
        return {
            **state,
            "customer_context": {"customer_id": customer_id, "error": str(e)},
            "order_found": False,
            "order_id_provided": False,
            "amount_mismatch": False,
            "error": f"Context fetch failed: {str(e)}",
            "steps_taken": steps,
        }
