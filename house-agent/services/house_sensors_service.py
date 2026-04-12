from __future__ import annotations

from typing import Any

from services.loxone_service import (
    get_loxone_structure_summary,
    get_room_climate_summary,
    get_sensor_inventory,
)
from routes.loxone_routes import (
    _ai_fetch_history,
    _ai_group_room_states,
    _ai_latest_per_state,
    _ai_presence_items,
    _ai_binary_on_items,
)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _normalize_room_name(room: str | None) -> str | None:
    if room is None:
        return None
    room = str(room).strip()
    if not room:
        return None
    if room.lower() == "not assigned":
        return None
    return room


def _get_room_list() -> list[str]:
    structure = get_loxone_structure_summary()
    if structure.get("status") != "ok":
        return []

    rooms = structure.get("rooms", []) or []
    cleaned = []

    for room in rooms:
        room_name = _normalize_room_name(room)
        if room_name:
            cleaned.append(room_name)

    return sorted(set(cleaned))


def _clean_target_temperature(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None

    if numeric <= 0:
        return None

    return round(numeric, 2)


def _compact_presence_source(item: dict) -> dict:
    return {
        "control_name": item.get("control_name"),
        "control_uuid": item.get("control_uuid"),
        "sensor_type": item.get("sensor_type"),
        "state_key": item.get("state_key"),
        "value": item.get("value"),
        "time": item.get("time"),
    }


def _build_presence_map(items: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}

    for item in items:
        room = _normalize_room_name(item.get("room"))
        if not room:
            continue

        sensor_type = str(item.get("sensor_type") or "").strip().lower()
        state_key = str(item.get("state_key") or "").strip()
        is_active = bool(item.get("is_active"))
        value = item.get("value")
        time_value = item.get("time")

        bucket = result.setdefault(
            room,
            {
                "presence": {
                    "is_active": False,
                    "last_seen": None,
                    "event_count_hint": None,
                    "sources": [],
                },
                "motion": {
                    "is_active": False,
                    "last_seen": None,
                    "sources": [],
                },
            },
        )

        compact = _compact_presence_source(item)

        if sensor_type == "motion":
            if state_key == "active":
                bucket["motion"]["sources"].append(compact)
                bucket["motion"]["is_active"] = is_active
                bucket["motion"]["last_seen"] = time_value
        else:
            if state_key == "active":
                bucket["presence"]["sources"].append(compact)
                bucket["presence"]["is_active"] = is_active
                bucket["presence"]["last_seen"] = time_value
            elif state_key == "events":
                bucket["presence"]["sources"].append(compact)
                numeric = _safe_float(value)
                bucket["presence"]["event_count_hint"] = int(numeric) if numeric is not None else None
            elif state_key == "activeSince":
                bucket["presence"]["sources"].append(compact)

    return result


def _classify_access_security_signal(signal: dict) -> str:
    state_key = str(signal.get("state_key") or "").strip().lower()
    sensor_type = str(signal.get("sensor_type") or "").strip().lower()
    control_name = str(signal.get("control_name") or "").strip().lower()
    numeric = _safe_float(signal.get("value"))

    if state_key in {"alarmlevel", "active", "isalarmactive", "acousticalarm", "resetactive"} and numeric and numeric > 0:
        return "alert"

    if state_key in {"keypadauthtype", "isenabled", "armed", "isleaveactive", "level", "status"} and numeric and numeric > 0:
        return "status"

    if sensor_type == "security" and numeric and numeric > 0:
        return "status"

    if "alarm" in control_name and numeric and numeric > 0:
        return "status"

    return "other"


def _build_activity_map(room_activity_items: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}

    for item in room_activity_items:
        room = _normalize_room_name(item.get("room"))
        if not room:
            continue

        on_items = item.get("on_items", []) or []

        lighting_active_controls = []
        access_security_active = []
        access_security_alerts = []
        access_security_status = []

        for sub in on_items:
            domain = str(sub.get("domain") or "").strip().lower()

            compact = {
                "control_name": sub.get("control_name"),
                "control_uuid": sub.get("control_uuid"),
                "sensor_type": sub.get("sensor_type"),
                "state_key": sub.get("state_key"),
                "value": sub.get("value"),
                "time": sub.get("time"),
            }

            if domain == "lighting":
                lighting_active_controls.append(compact)

            if domain in {"access", "security"}:
                access_security_active.append(compact)
                signal_class = _classify_access_security_signal(compact)
                if signal_class == "alert":
                    access_security_alerts.append(compact)
                elif signal_class == "status":
                    access_security_status.append(compact)

        result[room] = {
            "activity": {
                "binary_on_count": item.get("binary_on_count", 0),
                "binary_state_count": item.get("binary_state_count", 0),
                "telemetry_count": item.get("telemetry_count", 0),
                "latest_time": item.get("latest_time"),
            },
            "lighting": {
                "is_on": len(lighting_active_controls) > 0 if lighting_active_controls else False,
                "active_controls": lighting_active_controls,
            },
            "access_security": {
                "active_signals": access_security_active,
                "alert_signals": access_security_alerts,
                "status_signals": access_security_status,
            },
        }

    return result


def _build_inventory_map() -> dict[str, dict]:
    inventory = get_sensor_inventory()
    items = inventory.get("items", []) if isinstance(inventory, dict) else []

    result: dict[str, dict] = {}

    for item in items:
        room = _normalize_room_name(item.get("room_name"))
        if not room:
            continue

        domain = str(item.get("domain") or "").strip().lower()

        bucket = result.setdefault(
            room,
            {
                "lighting_known_controls": [],
                "access_security_known_controls": [],
            },
        )

        compact = {
            "name": item.get("name"),
            "uuid": item.get("uuid"),
            "sensor_type": item.get("sensor_type"),
            "type": item.get("type"),
            "state_keys": item.get("state_keys", []),
        }

        if domain == "lighting":
            bucket["lighting_known_controls"].append(compact)

        if domain in {"access", "security"}:
            bucket["access_security_known_controls"].append(compact)

    return result


def _compact_climate(room: str) -> dict:
    climate = get_room_climate_summary(room)
    if not isinstance(climate, dict) or climate.get("status") != "ok":
        return {
            "temperature_actual": None,
            "temperature_target": None,
            "humidity": None,
            "co2": None,
            "open_window": None,
            "operating_mode": None,
        }

    return {
        "temperature_actual": climate.get("temperature_actual"),
        "temperature_target": _clean_target_temperature(climate.get("temperature_target")),
        "humidity": climate.get("humidity"),
        "co2": climate.get("co2"),
        "open_window": bool(climate.get("open_window")) if climate.get("open_window") is not None else None,
        "operating_mode": climate.get("operating_mode"),
    }


def _derive_room_status(room_payload: dict) -> str:
    if room_payload["presence"]["is_active"]:
        return "occupied"

    if room_payload["motion"]["is_active"]:
        return "motion_detected"

    if room_payload["lighting"]["is_on"]:
        return "active_no_presence"

    if room_payload["activity"]["binary_on_count"] > 0:
        return "active_no_presence"

    if room_payload["has_any_sensor_data"]:
        return "idle"

    return "unknown"


def get_house_sensors(minutes: int = 60, limit: int = 8000) -> dict:
    rooms = _get_room_list()

    history = _ai_fetch_history(minutes=minutes, room=None, limit=limit)
    if history.get("status") != "ok":
        return {
            "status": "error",
            "message": history.get("message") or history.get("error") or "Failed to load Loxone history",
            "minutes": minutes,
            "room_count": 0,
            "rooms": [],
        }

    history_items = history.get("items", []) or []

    presence_items = _ai_presence_items(history_items)
    room_activity_items = _ai_group_room_states(history_items)
    binary_on_items = _ai_binary_on_items(history_items)
    latest_state_map = _ai_latest_per_state(history_items)

    presence_map = _build_presence_map(presence_items)
    activity_map = _build_activity_map(room_activity_items)
    inventory_map = _build_inventory_map()

    motion_active_rooms = []
    presence_active_rooms = []
    lighting_active_rooms = []
    occupied_rooms = []

    result_rooms = []

    for room in rooms:
        climate = _compact_climate(room)

        presence_block = presence_map.get(room, {}).get(
            "presence",
            {
                "is_active": False,
                "last_seen": None,
                "event_count_hint": None,
                "sources": [],
            },
        )

        motion_block = presence_map.get(room, {}).get(
            "motion",
            {
                "is_active": False,
                "last_seen": None,
                "sources": [],
            },
        )

        activity_block = activity_map.get(room, {}).get(
            "activity",
            {
                "binary_on_count": 0,
                "binary_state_count": 0,
                "telemetry_count": 0,
                "latest_time": None,
            },
        )

        lighting_block = activity_map.get(room, {}).get(
            "lighting",
            {
                "is_on": False,
                "active_controls": [],
            },
        )

        access_security_block = activity_map.get(room, {}).get(
            "access_security",
            {
                "active_signals": [],
                "alert_signals": [],
                "status_signals": [],
            },
        )

        inventory_block = inventory_map.get(
            room,
            {
                "lighting_known_controls": [],
                "access_security_known_controls": [],
            },
        )

        has_any_sensor_data = any(
            [
                climate["temperature_actual"] is not None,
                climate["humidity"] is not None,
                climate["co2"] is not None,
                presence_block["is_active"],
                motion_block["is_active"],
                bool(lighting_block.get("known_controls", [])),
                bool(lighting_block.get("active_controls", [])),
                bool(inventory_block.get("lighting_known_controls", [])),
                bool(inventory_block.get("access_security_known_controls", [])),
                activity_block["binary_state_count"] > 0,
                activity_block["telemetry_count"] > 0,
            ]
        )

        room_payload = {
            "room": room,
            "has_any_sensor_data": has_any_sensor_data,
            "climate": climate,
            "presence": presence_block,
            "motion": motion_block,
            "lighting": {
                "is_on": lighting_block.get("is_on"),
                "active_controls": lighting_block.get("active_controls", []),
                "known_controls": inventory_block.get("lighting_known_controls", []),
            },
            "access_security": {
                "active_signals": access_security_block.get("active_signals", []),
                "alert_signals": access_security_block.get("alert_signals", []),
                "status_signals": access_security_block.get("status_signals", []),
                "known_controls": inventory_block.get("access_security_known_controls", []),
            },
            "activity": activity_block,
        }

        room_payload["room_status"] = _derive_room_status(room_payload)

        if room_payload["presence"]["is_active"]:
            presence_active_rooms.append(room)
            occupied_rooms.append(room)

        if room_payload["motion"]["is_active"]:
            motion_active_rooms.append(room)

        if room_payload["lighting"]["is_on"]:
            lighting_active_rooms.append(room)

        result_rooms.append(room_payload)

    return {
        "status": "ok",
        "minutes": minutes,
        "room_count": len(result_rooms),
        "rooms": result_rooms,
        "summary": {
            "presence_active_rooms": sorted(presence_active_rooms),
            "motion_active_rooms": sorted(motion_active_rooms),
            "lighting_active_rooms": sorted(lighting_active_rooms),
            "occupied_rooms": sorted(occupied_rooms),
            "history_items_seen": len(history_items),
            "binary_active_items_seen": len(binary_on_items),
            "latest_state_count": len(latest_state_map),
        },
    }
