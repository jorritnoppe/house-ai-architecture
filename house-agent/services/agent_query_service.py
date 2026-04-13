from __future__ import annotations

from typing import Any, Dict

from services.agent_router_bridge import handle_house_or_ai_question
from services.agent_service import handle_agent_question


def run_agent_query(question: str) -> Dict[str, Any]:
    question = str(question or "").strip()
    q = question.lower()

    if not question:
        return {
            "status": "error",
            "mode": "agent_query",
            "answer": "Missing question.",
            "intents": [],
        }

    # Hard-priority house intelligence routing.
    # These questions must never be allowed to fall into unrelated direct-tool
    # matchers such as APC or generic device summaries.
    zone_room_intel_phrases = [
        "is anyone downstairs",
        "anyone downstairs",
        "is anyone upstairs",
        "anyone upstairs",
        "is anyone in the attic",
        "anyone in the attic",
        "which rooms downstairs are occupied",
        "what rooms downstairs are occupied",
        "which downstairs rooms are occupied",
        "what downstairs rooms are occupied",
        "which rooms upstairs are occupied",
        "what rooms upstairs are occupied",
        "which upstairs rooms are occupied",
        "what upstairs rooms are occupied",
        "which rooms downstairs are being used",
        "what rooms downstairs are being used",
        "which downstairs rooms are being used",
        "what downstairs rooms are being used",
        "which rooms upstairs are being used",
        "what rooms upstairs are being used",
        "which upstairs rooms are being used",
        "what upstairs rooms are being used",
        "attic occupancy",
        "upstairs occupancy",
        "downstairs occupancy",
    ]

    if any(phrase in q for phrase in zone_room_intel_phrases):
        return handle_house_or_ai_question(question)

    # Normal house / AI router path.
    result = handle_house_or_ai_question(question)
    if isinstance(result, dict) and result.get("status") == "ok":
        return result

    # Fallback general agent path.
    fallback = handle_agent_question(question)
    if isinstance(fallback, dict):
        fallback.setdefault("mode", "fallback_agent")
        return fallback

    return {
        "status": "ok",
        "mode": "fallback_agent",
        "answer": str(fallback),
        "intents": [],
    }

