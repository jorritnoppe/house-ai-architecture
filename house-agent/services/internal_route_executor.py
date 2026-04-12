from __future__ import annotations

from typing import Any, Dict

from services.power_service import (
    get_power_now_data,
    get_energy_summary_data,
    get_energy_today_data,
)

# Reuse the existing Loxone AI-history helpers directly
from routes.loxone_routes import (
    _ai_fetch_history,
    _ai_presence_items,
    _ai_telemetry_latest,
    _ai_group_room_states,
)

from services.netdata_service import get_all_nodes_overview, get_alarms, get_node_summary
from services.service_health_service import get_local_service_health, get_service_health_for_node, get_services_overview
from services.house_state_service import get_house_state
from services.unified_playback_state_service import get_unified_playback_state

from services.energy_service import energy_service







def _execute_loxone_history_presence(params: Dict[str, Any]) -> Dict[str, Any]:
    minutes = int((params or {}).get("minutes", 60))
    limit = int((params or {}).get("limit", 5000))
    room = (params or {}).get("room") or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return data

    items = _ai_presence_items(data.get("items", []))
    return {
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    }


def _execute_loxone_history_telemetry_latest(params: Dict[str, Any]) -> Dict[str, Any]:
    minutes = int((params or {}).get("minutes", 120))
    limit = int((params or {}).get("limit", 8000))
    room = (params or {}).get("room") or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return data

    items = _ai_telemetry_latest(data.get("items", []))

    filtered_items = []
    for item in items:
        item_room = item.get("room")
        state_key = item.get("state_key")
        value = item.get("value")

        if item_room == "Not Assigned":
            continue

        if state_key not in {"tempActual", "humidityActual"}:
            continue

        if value in (None, -1000.0, -999.0):
            continue

        if state_key == "humidityActual":
            try:
                if float(value) == 0.0:
                    continue
            except (TypeError, ValueError):
                continue

        filtered_items.append(item)

    return {
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(filtered_items),
        "items": filtered_items,
    }


def _execute_loxone_history_room_activity(params: Dict[str, Any]) -> Dict[str, Any]:
    minutes = int((params or {}).get("minutes", 60))
    limit = int((params or {}).get("limit", 8000))
    room = (params or {}).get("room") or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return data

    items = _ai_group_room_states(data.get("items", []))
    return {
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "room_count": len(items),
        "items": items,
    }


def execute_internal_route(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    params = params or {}

    if path == "/ai/power_now":
        return get_power_now_data()

    if path == "/ai/energy_summary":
        return get_energy_summary_data()

    if path == "/ai/energy_today":
        return get_energy_today_data()

    if path == "/ai/loxone_history_presence_ai":
        return _execute_loxone_history_presence(params)

    if path == "/ai/loxone_history_telemetry_latest":
        return _execute_loxone_history_telemetry_latest(params)

    if path == "/ai/loxone_history_room_activity_ai":
        return _execute_loxone_history_room_activity(params)

    if path == "/ai/nodes/health":
        overview = get_all_nodes_overview()
        result = {}

        for node, entry in overview.items():
            if entry.get("status") != "ok":
                result[node] = {
                    "status": "offline_or_error",
                    "error": entry.get("error")
                }
                continue

            summary = entry.get("summary", {})
            result[node] = {
                "status": summary.get("health_status", "ok"),
                "cpu_total_percent": summary.get("cpu_total_percent"),
                "ram_used_percent": summary.get("ram_used_percent"),
                "load1": summary.get("load1"),
                "active_alarm_count": summary.get("active_alarm_count", 0)
            }

        return {
            "status": "ok",
            "data": result
        }

    if path == "/ai/nodes/overview":
        return {
            "status": "ok",
            "data": get_all_nodes_overview()
        }

    if path == "/ai/node/summary":
        node = (params or {}).get("node")
        if not node:
            raise ValueError("Missing node parameter")
        return {
            "status": "ok",
            "data": get_node_summary(node)
        }

    if path == "/ai/node/alerts":
        node = (params or {}).get("node")
        if not node:
            raise ValueError("Missing node parameter")
        return {
            "status": "ok",
            "data": get_alarms(node)
        }


    if path == "/ai/service/health":
        return {
            "status": "ok",
            "data": get_local_service_health()
        }

    if path == "/ai/service/summary":
        node = (params or {}).get("node", "ai-server")
        return {
            "status": "ok",
            "data": get_service_health_for_node(node)
        }

    if path == "/ai/services/overview":
        return {
            "status": "ok",
            "data": get_services_overview()
        }


    if path == "/ai/unified_energy_summary":
        return energy_service.get_energy_ai_summary()

    if path == "/ai/unified_energy_snapshot":
        return energy_service.get_live_snapshot()


    if path == "/ai/playback_state":
        return get_unified_playback_state(cooldown_seconds=2)

    if path == "/ai/house_state":
        return get_house_state()


    raise ValueError(f"No internal executor mapped for route: {path}")
