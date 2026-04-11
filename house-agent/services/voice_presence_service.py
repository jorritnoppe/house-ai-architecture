from __future__ import annotations

from typing import Any, Dict, Optional

from services.internal_route_executor import execute_internal_route


def _presence_flags(items: list[dict]) -> dict:
    active = False
    recent = False

    for item in items or []:
        recent = True

        if item.get("state_key") == "active" and item.get("is_active") is True:
            active = True
            break

    return {
        "presence_active": active,
        "presence_recent": recent,
    }


def build_presence_validation(primary_room: Optional[str], minutes: int = 15) -> Dict[str, Any]:
    """
    Uses the node-mapped room as primary truth, then validates against recent Loxone presence.
    Does not hard-block interactions. It only adds confidence and debug signals.
    """
    result: Dict[str, Any] = {
        "status": "ok",
        "primary_room": primary_room,
        "minutes": minutes,
        "snapshot": {},
        "presence_active": False,
        "presence_recent": False,
        "confidence_boost": 0.0,
        "reasons": [],
        "raw_count": 0,
    }

    if not primary_room:
        result["status"] = "error"
        result["reasons"].append("no primary room provided")
        return result

    try:
        data = execute_internal_route(
            "/ai/loxone_history_presence_ai",
            {
                "room": primary_room,
                "minutes": minutes,
                "limit": 5000,
            },
        )

        items = data.get("items", []) or []
        flags = _presence_flags(items)

        result["snapshot"] = {
            primary_room: flags["presence_active"]
        }
        result["presence_active"] = flags["presence_active"]
        result["presence_recent"] = flags["presence_recent"]
        result["raw_count"] = len(items)

        if flags["presence_active"]:
            result["confidence_boost"] = 0.22
            result["reasons"].append(f"presence active in {primary_room}")
        elif flags["presence_recent"]:
            result["confidence_boost"] = 0.12
            result["reasons"].append(f"recent presence found in {primary_room}")
        else:
            result["confidence_boost"] = -0.08
            result["reasons"].append(f"no recent presence found in {primary_room}")

        result["reasons"].insert(0, f"node mapped to {primary_room}")
        return result

    except Exception as exc:
        result["status"] = "error"
        result["reasons"].append(str(exc))
        result["snapshot"] = {primary_room: False}
        return result
