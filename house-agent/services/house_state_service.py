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


SOLAR_ACTIVE_THRESHOLD_KW = 0.15
IMPORT_EXPORT_MEANINGFUL_THRESHOLD_KW = 0.20
HOUSE_LOAD_LOW_THRESHOLD_KW = 0.40
HOUSE_LOAD_HIGH_THRESHOLD_KW = 2.50


def _safe_call(fn, default):
    try:
        return fn()
    except Exception as exc:
        result = dict(default)
        result["status"] = "error"
        result["error"] = str(exc)
        return result


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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
    excess_energy_available_kw = None
    excess_energy_state = "none"
    excess_energy_reason = None



    if isinstance(energy_flow, dict):
        interpreted_house_load_kw = _safe_float(energy_flow.get("estimated_house_load_kw"))
        interpreted_grid_import_kw = _safe_float(energy_flow.get("grid_import_kw"))
        interpreted_grid_export_kw = _safe_float(energy_flow.get("grid_export_kw"))
        interpreted_solar_power_kw = _safe_float(energy_flow.get("solar_power_kw"))
        excess_energy_available_kw = _safe_float(energy_flow.get("excess_energy_available_kw"))
        excess_energy_state = energy_flow.get("excess_energy_state") or "none"
        excess_energy_reason = energy_flow.get("excess_energy_reason")



    solar_active = bool(
        interpreted_solar_power_kw is not None and interpreted_solar_power_kw >= SOLAR_ACTIVE_THRESHOLD_KW
    )
    importing_from_grid = bool(
        interpreted_grid_import_kw is not None and interpreted_grid_import_kw >= IMPORT_EXPORT_MEANINGFUL_THRESHOLD_KW
    )
    exporting_excess = bool(
        interpreted_grid_export_kw is not None and interpreted_grid_export_kw >= IMPORT_EXPORT_MEANINGFUL_THRESHOLD_KW
    )
    solar_covering_load = bool(
        solar_active
        and interpreted_house_load_kw is not None
        and interpreted_solar_power_kw is not None
        and interpreted_house_load_kw > 0
        and interpreted_solar_power_kw >= interpreted_house_load_kw * 0.8
    )

    house_load_band = "unknown"
    if interpreted_house_load_kw is not None:
        if interpreted_house_load_kw < HOUSE_LOAD_LOW_THRESHOLD_KW:
            house_load_band = "low"
        elif interpreted_house_load_kw >= HOUSE_LOAD_HIGH_THRESHOLD_KW:
            house_load_band = "high"
        else:
            house_load_band = "normal"

    energy_mode = "unknown"
    if interpreted_house_load_kw is None:
        energy_mode = "unknown"
    elif solar_active and exporting_excess:
        energy_mode = "exporting_excess"
    elif solar_covering_load:
        energy_mode = "solar_covering_load"
    elif importing_from_grid:
        energy_mode = "grid_assisted"
    else:
        energy_mode = "stable"

    climate_summary = {
        "min_temp_c": None,
        "max_temp_c": None,
        "min_humidity_percent": None,
        "max_humidity_percent": None,
        "room_count": 0,
    }

    temp_values = []
    humidity_values = []
    climate_rooms = set()

    for item in telemetry_items:
        room = item.get("room")
        state_key = item.get("state_key")
        value = _safe_float(item.get("value"))

        if room:
            climate_rooms.add(room)

        if value is None:
            continue

        if state_key == "tempActual":
            temp_values.append(value)
        elif state_key == "humidityActual":
            humidity_values.append(value)

    if temp_values:
        climate_summary["min_temp_c"] = round(min(temp_values), 1)
        climate_summary["max_temp_c"] = round(max(temp_values), 1)

    if humidity_values:
        climate_summary["min_humidity_percent"] = round(min(humidity_values), 1)
        climate_summary["max_humidity_percent"] = round(max(humidity_values), 1)

    climate_summary["room_count"] = len(climate_rooms)

    quiet_now = None
    if isinstance(playback, dict):
        try:
            playback_active = bool(
                playback.get("effective", {}).get("is_active")
                or playback.get("summary", {}).get("any_playing")
                or playback.get("any_playing")
            )
            quiet_now = not playback_active
        except Exception:
            quiet_now = None

    offline_nodes = []
    warning_nodes_count = 0
    if isinstance(nodes_health, dict) and nodes_health.get("status") == "ok":
        for node_name, entry in (nodes_health.get("data") or {}).items():
            node_status = (entry or {}).get("status")
            if node_status in {"offline_or_error", "offline"}:
                offline_nodes.append(node_name)
            elif node_status not in {None, "ok", "healthy"}:
                warning_nodes_count += 1



    service_warning_hosts = []
    monitoring_unavailable_nodes = []

    if isinstance(services_overview, dict):
        for node_name, entry in services_overview.items():
            if not isinstance(entry, dict):
                continue

            overall_status = str(entry.get("overall_status") or "").lower()

            if overall_status in {"error", "offline", "offline_or_error"}:
                monitoring_unavailable_nodes.append(node_name)
                continue

            if overall_status == "warning":
                service_warning_hosts.append(node_name)
                continue

            warnings = entry.get("warnings") or []
            if warnings:
                service_warning_hosts.append(node_name)




    return {
        "status": "ok",
        "power": power,
        "energy_summary": energy_summary,
        "energy_snapshot": energy_snapshot,
        "energy_flow": energy_flow,
        "climate_summary": climate_summary,
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
            "solar_active": solar_active,
            "solar_covering_load": solar_covering_load,
            "exporting_excess": exporting_excess,
            "importing_from_grid": importing_from_grid,
            "house_load_band": house_load_band,
            "energy_mode": energy_mode,
            "quiet_now": quiet_now,
            "offline_nodes": offline_nodes,
            "warning_nodes_count": warning_nodes_count,
            "service_warning_hosts": service_warning_hosts,
            "monitoring_unavailable_nodes": monitoring_unavailable_nodes,
            "excess_energy_available_kw": excess_energy_available_kw,
            "excess_energy_state": excess_energy_state,
            "excess_energy_reason": excess_energy_reason,
        },
    }
