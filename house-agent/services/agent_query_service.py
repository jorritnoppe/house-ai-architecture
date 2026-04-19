from __future__ import annotations

from typing import Any, Dict

from services.agent_router_bridge import handle_house_or_ai_question


def run_agent_query(question: str) -> Dict[str, Any]:
    question = str(question or "").strip()

    if not question:
        return {
            "status": "error",
            "mode": "validation_error",
            "intents": [],
            "used_tools": [],
            "tool_data": {},
            "answer": "No question was provided.",
        }

    try:
        result = handle_house_or_ai_question(question)

        if isinstance(result, dict):
            result.setdefault("status", "ok")
            result.setdefault("question", question)
            result.setdefault("intents", [])
            result.setdefault("used_tools", [])
            result.setdefault("tool_data", {})
            return result

        return {
            "status": "ok",
            "mode": "router_bridge",
            "question": question,
            "intents": [],
            "used_tools": [],
            "tool_data": {},
            "answer": str(result),
        }

    except Exception as exc:
        return {
            "status": "error",
            "mode": "router_bridge_error",
            "question": question,
            "intents": [],
            "used_tools": [],
            "tool_data": {
                "error_type": type(exc).__name__,
            },
            "answer": f"Agent query failed: {exc}",
        }
