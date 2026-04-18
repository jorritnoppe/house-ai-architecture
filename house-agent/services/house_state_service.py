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
from services.house_sensors_service import get_house_sensors
from services.unifi_collector import collector as unifi_collector






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




def _build_network_interpretation(network: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(network, dict):
        return {
            "status": "error",
            "spoken_summary": "Network data is unavailable.",
            "overall": "unknown",
            "devices_online": 0,
            "devices_offline": 0,
            "clients_active": 0,
            "gateway_cpu_percent": None,
            "gateway_mem_percent": None,
            "wan_latency_ms": None,
            "unknown_clients": 0,
            "critical_devices_offline": [],
            "backend": None,
            "snapshot_age_seconds": None,
            "freshness": "unknown",
            "is_stale": True,
            "timestamp": None,
        }

    status = str(network.get("status") or "unknown")
    summary = network.get("summary") or {}
    last_error = network.get("last_error")
    backend = network.get("backend")
    timestamp = network.get("timestamp")

    overall = str(summary.get("overall") or "unknown")
    devices_online = int(summary.get("device_count_online") or 0)
    devices_offline = int(summary.get("device_count_offline") or 0)
    clients_active = int(summary.get("client_count_active") or 0)
    unknown_clients = max(
        0,
        int(clients_active - int(summary.get("mapped_clients") or 0)),
    )
    critical_devices_offline = list(summary.get("critical_offline") or [])

    gateway_cpu_percent = None
    gateway_mem_percent = None
    wan_latency_ms = None

    for row in summary.get("site_health_rows", []):
        if not isinstance(row, dict):
            continue
        if row.get("subsystem") != "wan":
            continue

        gw_stats = row.get("gw_system-stats", {}) or {}
        gateway_cpu_percent = _safe_float(gw_stats.get("cpu"))
        gateway_mem_percent = _safe_float(gw_stats.get("mem"))

        wan_info = row.get("uptime_stats", {}).get("WAN", {}) or {}
        wan_latency_ms = _safe_float(wan_info.get("latency_average"))
        break

    snapshot_age_seconds = None
    freshness = "unknown"
    is_stale = True

    if isinstance(timestamp, str) and timestamp.strip():
        try:
            from datetime import datetime, timezone

            parsed = datetime.fromisoformat(timestamp)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)
            snapshot_age_seconds = max(
                0,
                int((now_utc - parsed.astimezone(timezone.utc)).total_seconds())
            )

            if snapshot_age_seconds <= 120:
                freshness = "fresh"
                is_stale = False
            elif snapshot_age_seconds <= 600:
                freshness = "aging"
                is_stale = False
            else:
                freshness = "stale"
                is_stale = True
        except Exception:
            snapshot_age_seconds = None
            freshness = "unknown"
            is_stale = True

    if status != "ok":
        spoken_summary = "Network data is currently unavailable."
        if last_error:
            spoken_summary = f"Network data is currently unavailable. Last error: {last_error}"
    elif freshness == "stale":
        if snapshot_age_seconds is not None:
            spoken_summary = (
                f"Network data is stale and about {snapshot_age_seconds} seconds old. "
                f"The last known state showed {devices_online} infrastructure devices online "
                f"and {clients_active} active clients."
            )
        else:
            spoken_summary = (
                f"Network data may be stale. The last known state showed {devices_online} "
                f"infrastructure devices online and {clients_active} active clients."
            )
    elif critical_devices_offline:
        spoken_summary = (
            f"The network has issues. {len(critical_devices_offline)} critical devices are offline."
        )
    elif devices_offline > 0:
        spoken_summary = (
            f"The network is mostly healthy. {devices_online} devices are online, "
            f"{devices_offline} are offline, and {clients_active} clients are active."
        )
    elif freshness == "aging":
        spoken_summary = (
            f"The network looks healthy, but the data is {snapshot_age_seconds} seconds old. "
            f"{devices_online} infrastructure devices are online and {clients_active} clients are active."
        )
    else:
        spoken_summary = (
            f"The network looks healthy. {devices_online} infrastructure devices are online "
            f"and {clients_active} clients are active."
        )

    return {
        "status": status,
        "spoken_summary": spoken_summary,
        "overall": overall,
        "devices_online": devices_online,
        "devices_offline": devices_offline,
        "clients_active": clients_active,
        "gateway_cpu_percent": gateway_cpu_percent,
        "gateway_mem_percent": gateway_mem_percent,
        "wan_latency_ms": wan_latency_ms,
        "unknown_clients": unknown_clients,
        "critical_devices_offline": critical_devices_offline,
        "backend": backend,
        "last_error": last_error,
        "timestamp": timestamp,
        "snapshot_age_seconds": snapshot_age_seconds,
        "freshness": freshness,
        "is_stale": is_stale,
    }


def _get_network_summary() -> Dict[str, Any]:
    data = unifi_collector.get_cache()
    if not isinstance(data, dict):
        return {
            "status": "error",
            "summary": {},
            "devices": [],
            "clients": [],
            "events": [],
            "alarms": [],
            "topology_lite": {},
            "last_error": "Invalid UniFi cache payload",
            "backend": "sqlite",
        }

    result = dict(data)
    result["backend"] = result.get("backend") or "sqlite"
    return result




def get_house_state() -> Dict[str, Any]:
    power = _safe_call(get_power_now_data, {"status": "error"})
    energy_summary = _safe_call(get_energy_summary_data, {"status": "error"})
    energy_snapshot = _safe_call(energy_service.get_live_snapshot, {"status": "error"})
    energy_flow = _safe_call(energy_service.get_power_flow_summary, {"status": "error"})

    house_sensors = _safe_call(
        lambda: get_house_sensors(minutes=60, limit=8000),
        {"status": "error"},
    )

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

    network = _safe_call(
        _get_network_summary,
        {"status": "error"},
    )

    network_interpretation = _safe_call(
        lambda: _build_network_interpretation(network),
        {"status": "error", "spoken_summary": "Network interpretation unavailable."},
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



    occupied_rooms = []
    lighting_active_rooms = []
    rooms_with_sensor_data = []
    rooms_idle = []
    rooms_unknown = []

    if isinstance(house_sensors, dict) and house_sensors.get("status") == "ok":
        for room_entry in (house_sensors.get("rooms") or []):
            room_name = room_entry.get("room")
            room_status = room_entry.get("room_status")
            has_any_sensor_data = bool(room_entry.get("has_any_sensor_data"))

            if has_any_sensor_data and room_name:
                rooms_with_sensor_data.append(room_name)

            if room_status == "occupied" and room_name:
                occupied_rooms.append(room_name)
            elif room_status == "idle" and room_name:
                rooms_idle.append(room_name)
            elif room_status == "unknown" and room_name:
                rooms_unknown.append(room_name)

            if ((room_entry.get("lighting") or {}).get("is_on")) and room_name:
                lighting_active_rooms.append(room_name)




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
        "house_sensors": house_sensors,
        "summary": {
            "current_power_watts": power.get("power_watts"),
            "telemetry_rooms_seen": len(rooms_seen),
            "active_audio_rooms": active_rooms,
            "voice_nodes_online": ((voice_nodes.get("summary") or {}).get("online") if isinstance(voice_nodes, dict) else None),
            "network_interpretation": network_interpretation if isinstance(network_interpretation, dict) else {},
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
            "occupied_rooms": occupied_rooms,
            "occupied_room_count": len(occupied_rooms),
            "lighting_active_rooms": lighting_active_rooms,
            "lighting_active_room_count": len(lighting_active_rooms),
            "rooms_with_sensor_data": rooms_with_sensor_data,
            "rooms_with_sensor_data_count": len(rooms_with_sensor_data),
            "rooms_idle": rooms_idle,
            "rooms_idle_count": len(rooms_idle),
            "rooms_unknown": rooms_unknown,
            "rooms_unknown_count": len(rooms_unknown),
        },
    }

def get_daily_house_summary() -> Dict[str, Any]:
    house_state = get_house_state()
    if not isinstance(house_state, dict):
        return {
            "status": "error",
            "message": "House state is unavailable",
        }

    summary = house_state.get("summary") or {}
    climate = house_state.get("climate_summary") or {}
    energy_summary = house_state.get("energy_summary") or {}
    energy_flow = house_state.get("energy_flow") or {}
    telemetry = house_state.get("telemetry") or {}
    audio = house_state.get("audio") or {}
    crypto = house_state.get("crypto") or {}
    voice_nodes = house_state.get("voice_nodes") or {}

    occupied_rooms = summary.get("occupied_rooms") or []
    lighting_active_rooms = summary.get("lighting_active_rooms") or []
    offline_nodes = summary.get("offline_nodes") or []
    service_warning_hosts = summary.get("service_warning_hosts") or []
    monitoring_unavailable_nodes = summary.get("monitoring_unavailable_nodes") or []

    interpreted_house_load_kw = summary.get("interpreted_house_load_kw")
    interpreted_solar_power_kw = summary.get("interpreted_solar_power_kw")
    interpreted_grid_import_kw = summary.get("interpreted_grid_import_kw")
    interpreted_grid_export_kw = summary.get("interpreted_grid_export_kw")
    energy_mode = summary.get("energy_mode") or "unknown"
    quiet_now = summary.get("quiet_now")

    room_count = climate.get("room_count") or 0
    min_temp_c = climate.get("min_temp_c")
    max_temp_c = climate.get("max_temp_c")
    min_humidity_percent = climate.get("min_humidity_percent")
    max_humidity_percent = climate.get("max_humidity_percent")

    voice_online = None
    if isinstance(voice_nodes, dict):
        voice_online = ((voice_nodes.get("summary") or {}).get("online"))

    crypto_total_value = None
    if isinstance(crypto, dict):
        crypto_total_value = crypto.get("total_value")

    spoken_parts = []

    if interpreted_house_load_kw is not None:
        spoken_parts.append(f"Estimated house load is {interpreted_house_load_kw:.2f} kilowatts")

    if interpreted_solar_power_kw is not None and interpreted_solar_power_kw > 0:
        spoken_parts.append(f"solar production is {interpreted_solar_power_kw:.2f} kilowatts")

    if interpreted_grid_export_kw is not None and interpreted_grid_export_kw > 0.05:
        spoken_parts.append(f"the house is exporting {interpreted_grid_export_kw:.2f} kilowatts")
    elif interpreted_grid_import_kw is not None and interpreted_grid_import_kw > 0.05:
        spoken_parts.append(f"the house is importing {interpreted_grid_import_kw:.2f} kilowatts from the grid")

    if occupied_rooms:
        spoken_parts.append(
            "Likely occupied rooms are " + ", ".join(occupied_rooms[:6])
        )
    else:
        spoken_parts.append("No rooms currently show strong occupancy")

    if room_count:
        climate_bits = []
        if min_temp_c is not None and max_temp_c is not None:
            climate_bits.append(f"temperature ranges from {min_temp_c:.1f} to {max_temp_c:.1f} C")
        if min_humidity_percent is not None and max_humidity_percent is not None:
            climate_bits.append(f"humidity ranges from {min_humidity_percent:.1f} to {max_humidity_percent:.1f} percent")
        if climate_bits:
            spoken_parts.append("House climate: " + "; ".join(climate_bits))

    if offline_nodes:
        spoken_parts.append("Offline nodes: " + ", ".join(offline_nodes[:5]))

    if service_warning_hosts:
        spoken_parts.append("Service warnings on: " + ", ".join(service_warning_hosts[:5]))

    if monitoring_unavailable_nodes:
        spoken_parts.append("Monitoring unavailable for: " + ", ".join(monitoring_unavailable_nodes[:5]))

    if quiet_now is True:
        spoken_parts.append("The house is currently quiet")
    elif quiet_now is False:
        spoken_parts.append("Audio playback is currently active")

    spoken_summary = ". ".join(spoken_parts).strip()
    if spoken_summary and not spoken_summary.endswith("."):
        spoken_summary += "."

    return {
        "status": "ok",
        "generated_at": energy_summary.get("timestamp") or telemetry.get("timestamp"),
        "energy": {
            "mode": energy_mode,
            "estimated_house_load_kw": interpreted_house_load_kw,
            "solar_power_kw": interpreted_solar_power_kw,
            "grid_import_kw": interpreted_grid_import_kw,
            "grid_export_kw": interpreted_grid_export_kw,
            "excess_energy_available_kw": summary.get("excess_energy_available_kw"),
            "excess_energy_state": summary.get("excess_energy_state"),
            "provider_net_power_kw": energy_summary.get("provider_net_power_kw"),
            "current_average_demand_kw": energy_summary.get("current_average_demand_kw"),
        },
        "climate": {
            "room_count": room_count,
            "min_temp_c": min_temp_c,
            "max_temp_c": max_temp_c,
            "min_humidity_percent": min_humidity_percent,
            "max_humidity_percent": max_humidity_percent,
        },
        "activity": {
            "occupied_rooms": occupied_rooms,
            "occupied_room_count": len(occupied_rooms),
            "lighting_active_rooms": lighting_active_rooms,
            "lighting_active_room_count": len(lighting_active_rooms),
            "quiet_now": quiet_now,
            "active_audio_rooms": summary.get("active_audio_rooms") or [],
        },
        "infrastructure": {
            "offline_nodes": offline_nodes,
            "warning_nodes_count": summary.get("warning_nodes_count"),
            "service_warning_hosts": service_warning_hosts,
            "monitoring_unavailable_nodes": monitoring_unavailable_nodes,
            "voice_nodes_online": voice_online,
        },
        "telemetry": {
            "rooms_seen": telemetry.get("rooms_seen") or [],
            "room_count": len(telemetry.get("rooms_seen") or []),
            "count": telemetry.get("count"),
            "minutes": telemetry.get("minutes"),
        },
        "crypto": {
            "total_value": crypto_total_value,
        },
        "spoken_summary": spoken_summary,
    }
