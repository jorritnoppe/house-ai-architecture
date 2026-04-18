from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime, timezone

from services.house_state_service import get_daily_house_summary
from services.waste_schedule_service import get_waste_schedule_summary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _safe_list(value):
    return value if isinstance(value, list) else []


def _join_natural(items: List[str]) -> str:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _build_warning_items(house: Dict[str, Any]) -> Dict[str, Any]:
    infra = _safe_dict(house.get("infrastructure"))
    warning_items: List[str] = []

    for node in _safe_list(infra.get("offline_nodes")):
        warning_items.append(f"offline node {node}")

    for host in _safe_list(infra.get("service_warning_hosts")):
        warning_items.append(f"service warning on {host}")

    for node in _safe_list(infra.get("monitoring_unavailable_nodes")):
        warning_items.append(f"monitoring unavailable for {node}")

    return {
        "status": "ok",
        "count": len(warning_items),
        "items": warning_items,
    }


def _build_spoken_summary(house: Dict[str, Any], waste: Dict[str, Any], warnings: Dict[str, Any]) -> str:
    parts: List[str] = ["Good evening."]

    house_spoken = str(house.get("spoken_summary") or "").strip()
    if house_spoken:
        parts.append(house_spoken)

    if waste.get("status") == "ok":
        spoken_tomorrow = str(waste.get("spoken_tomorrow") or "").strip()
        spoken_next = str(waste.get("spoken_next") or "").strip()

        if spoken_tomorrow:
            parts.append(f"Important reminder. {spoken_tomorrow}")
        elif spoken_next:
            parts.append(spoken_next)

    warning_items = warnings.get("items") or []
    if warning_items:
        parts.append("Current house warnings include " + _join_natural(warning_items[:3]) + ".")

    text = " ".join(part.strip() for part in parts if str(part).strip()).strip()
    if text and not text.endswith("."):
        text += "."
    return text or "Good evening. No evening briefing could be generated."


def get_evening_briefing() -> Dict[str, Any]:
    house = get_daily_house_summary()
    waste = get_waste_schedule_summary()
    warnings = _build_warning_items(house)

    payload = {
        "status": "ok",
        "generated_at": _utc_now_iso(),
        "house": house,
        "waste": waste,
        "warnings": warnings,
    }
    payload["spoken_summary"] = _build_spoken_summary(house, waste, warnings)
    return payload
