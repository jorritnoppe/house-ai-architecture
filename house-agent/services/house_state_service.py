from __future__ import annotations

from typing import Any, Dict

from extensions import crypto_tools
from services.netdata_service import get_all_nodes_overview
from services.service_health_service import get_services_overview
from services.unified_playback_state_service import get_unified_playback_state
from services.voice_node_registry_service import get_voice_node_registry
from routes.loxone_routes import _ai_fetch_history, _ai_telemetry_latest

from services.power_service import get_power_now_data, get_energy_summary_data
from services.energy_service import energy_service




def _safe_call(fn, default):
    try:
        return fn()
    except Exception as exc:
        result = dict(default)
        result["status"] = "error"
        result["error"] = str(exc)
        return result


def _get_nodes_health() -> Dict[str, Any]:
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


def _get_latest_telemetry(minutes: int = 120, room: str | None = None, limit: int = 8000) -> Dict[str, Any]:
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


def get_house_state() -> Dict[str, Any]:
    power = _safe_call(get_power_now_data, {"status": "error"})
    energy_summary = _safe_call(get_energy_summary_data, {"status": "error"})
    energy_snapshot = _safe_call(energy_service.get_live_snapshot, {"status": "error"})
    energy_flow = _safe_call(energy_service.get_power_flow_summary, {"status": "error"})

    telemetry = _safe_call(
        lambda: _get_latest_telemetry(minutes=120),
        {"status": "error"},
    )
    nodes_health = _safe_call(
        _get_nodes_health,
        {"status": "error"},
    )
    services_overview = _safe_call(
        get_services_overview,
        {"status": "error"},
    )
    playback = _safe_call(
        lambda: get_unified_playback_state(cooldown_seconds=2),
        {"status": "error"},
    )
    voice_nodes = _safe_call(
        lambda: get_voice_node_registry().get_summary(),
        {"status": "error"},
    )
    crypto_summary = _safe_call(
        lambda: crypto_tools.get_current_portfolio_summary(),
        {"status": "error"},
    )

    telemetry_items = telemetry.get("items", []) if isinstance(telemetry, dict) else []
    rooms_seen = sorted({item.get("room") for item in telemetry_items if item.get("room")})

    active_rooms = []
    pb_effective = playback.get("effective", {}) if isinstance(playback, dict) else {}
    if pb_effective.get("effective_target_room"):
        active_rooms.append(pb_effective["effective_target_room"])

    interpreted_house_load_kw = None
    interpreted_grid_import_kw = None
    interpreted_grid_export_kw = None
    interpreted_solar_power_kw = None

    if isinstance(energy_flow, dict):
        interpreted_house_load_kw = energy_flow.get("estimated_house_load_kw")
        interpreted_grid_import_kw = energy_flow.get("grid_import_kw")
        interpreted_grid_export_kw = energy_flow.get("grid_export_kw")
        interpreted_solar_power_kw = energy_flow.get("solar_power_kw")

    return {
        "status": "ok",
        "power": power,
        "energy_summary": energy_summary,
        "energy_snapshot": energy_snapshot,
        "energy_flow": energy_flow,
        "telemetry": {
            "status": telemetry.get("status"),
            "minutes": telemetry.get("minutes"),
            "count": telemetry.get("count"),
            "rooms_seen": rooms_seen,
            "items": telemetry_items,
        },
        "audio": playback,
        "voice_nodes": voice_nodes,
        "nodes_health": nodes_health,
        "services": services_overview,
        "crypto": crypto_summary,
        "summary": {
            "current_power_watts": power.get("power_watts"),
            "telemetry_rooms_seen": len(rooms_seen),
            "active_audio_rooms": active_rooms,
            "voice_nodes_online": ((voice_nodes.get("summary") or {}).get("online") if isinstance(voice_nodes, dict) else None),
            "crypto_total_value": crypto_summary.get("total_value") if isinstance(crypto_summary, dict) else None,
            "interpreted_house_load_kw": interpreted_house_load_kw,
            "interpreted_grid_import_kw": interpreted_grid_import_kw,
            "interpreted_grid_export_kw": interpreted_grid_export_kw,
            "interpreted_solar_power_kw": interpreted_solar_power_kw,
        },
    }
