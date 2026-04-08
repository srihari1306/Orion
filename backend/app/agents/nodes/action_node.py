import asyncio
from app.agents.state import AgentState
from app.agents.tools.internal_apis import issue_refund, issue_credit, trigger_replacement, reroute_shipment

def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

def action_node(state: AgentState) -> AgentState:
    resolution_path = state.get("resolution_path", "handoff")
    action_plan = state.get("action_plan") or {}
    customer_context = state.get("customer_context") or {}
    customer_id = state["customer_id"]
    steps = state.get("steps_taken", [])

    if resolution_path == "need_info":
        steps.append("action: need_info — requesting information from customer")
        return {
            **state,
            "action_result": {
                "path": "need_info",
                "executed": False,
                "missing_info": action_plan.get("missing_info", "order_id"),
                "reason": action_plan.get("reason", "Missing required information"),
            },
            "steps_taken": steps,
        }

    if resolution_path == "handoff":
        steps.append("action: handoff — no action executed")
        return {**state, "action_result": {"path": "handoff", "executed": False}, "steps_taken": steps}

    if resolution_path == "approval":
        steps.append("action: queued for approval")
        return {
            **state,
            "action_result": {"path": "approval", "executed": False, "queued": True},
            "steps_taken": steps,
        }

    action_type = action_plan.get("action_type", "closure")
    amount = action_plan.get("amount") or 0.0
    order_id = action_plan.get("order_id") or customer_context.get("order_id")

    if action_type in ("refund", "replacement", "reroute"):
        if not state.get("order_found", False):
            steps.append(f"action_blocked: order not found for {action_type}")
            return {
                **state,
                "action_result": {
                    "success": False,
                    "error": "Cannot execute: order not found in database",
                    "path": "auto_resolve",
                    "action_type": action_type,
                },
                "steps_taken": steps,
            }

        if action_type == "refund" and amount > 0:
            actual_amount = customer_context.get("order_amount", 0)
            if actual_amount and amount > actual_amount:
                steps.append(f"action_blocked: refund ${amount} exceeds order total ${actual_amount}")
                return {
                    **state,
                    "action_result": {
                        "success": False,
                        "error": f"Refund amount ${amount:.2f} exceeds order total ${actual_amount:.2f}",
                        "path": "auto_resolve",
                        "action_type": action_type,
                    },
                    "steps_taken": steps,
                }

        if not order_id or order_id in ("ORD-0000", "NOT_FOUND", "null", "None"):
            steps.append(f"action_blocked: no valid order_id for {action_type}")
            return {
                **state,
                "action_result": {
                    "success": False,
                    "error": "Cannot execute: no valid order ID",
                    "path": "auto_resolve",
                    "action_type": action_type,
                },
                "steps_taken": steps,
            }

    try:
        if action_type == "refund":
            result = _run_async(issue_refund(customer_id, amount, order_id))
        elif action_type == "credit":
            result = _run_async(issue_credit(customer_id, amount))
        elif action_type == "replacement":
            result = _run_async(trigger_replacement(order_id, []))
        elif action_type == "reroute":
            tracking = customer_context.get("tracking_number")
            if not tracking:
                steps.append("action_blocked: no tracking number for reroute")
                return {
                    **state,
                    "action_result": {"success": False, "error": "No tracking number available", "path": "auto_resolve"},
                    "steps_taken": steps,
                }
            result = _run_async(reroute_shipment(tracking))
        else:
            result = {"success": True, "message": f"Action '{action_type}' acknowledged", "executed": True}

        steps.append(f"action_executed: {action_type}")
        return {**state, "action_result": {**result, "action_type": action_type, "path": "auto_resolve"}, "steps_taken": steps}

    except Exception as e:
        steps.append(f"action_error: {str(e)}")
        return {
            **state,
            "action_result": {"success": False, "error": str(e), "path": "auto_resolve"},
            "error": f"Action execution failed: {str(e)}",
            "steps_taken": steps,
        }
