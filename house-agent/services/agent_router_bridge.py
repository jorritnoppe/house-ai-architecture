from __future__ import annotations

from typing import Any, Dict, Optional

from services.agent_executor import execute_safe_action
from services.agent_service import handle_agent_question
from services.house_ai_history_router import route_history_question
from services.action_auth_service import classify_action_auth
from services.pending_approval_service import get_pending_approval_service
from services.house_summary_policy import summarize_house_state

import os
import sqlite3
import threading

from datetime import datetime, timezone



def _extract_room_signal_snapshot(room_name, room_payload):
    """
    Normalize the real /ai/house_sensors room payload into the flat signal shape
    expected by the room reasoning layer.

    Input example:
    {
        "room": "bathroom",
        "presence": {"is_active": True, "last_seen": "..."},
        "motion": {"is_active": False, "last_seen": None},
        "lighting": {"is_on": False},
        "access_security": {"active_signals": [...]},
        "climate": {...},
        "activity": {"latest_time": "..."}
    }
    """
    payload = room_payload or {}

    presence_data = payload.get("presence") or {}
    motion_data = payload.get("motion") or {}
    lighting_data = payload.get("lighting") or {}
    access_data = payload.get("access_security") or {}
    climate_data = payload.get("climate") or {}
    activity_data = payload.get("activity") or {}

    active_access_signals = access_data.get("active_signals") or []
    status_signals = access_data.get("status_signals") or []

    access_active = bool(active_access_signals or status_signals)

    climate_active = any(
        value not in (None, 0, 0.0, False)
        for value in [
            climate_data.get("operating_mode"),
            climate_data.get("temperature_target"),
            climate_data.get("open_window"),
        ]
    )

    normalized = {
        "room": payload.get("room") or room_name,
        "room_status": payload.get("room_status"),
        "has_any_sensor_data": _safe_bool(payload.get("has_any_sensor_data")),

        "presence": _safe_bool(presence_data.get("is_active")),
        "motion": _safe_bool(motion_data.get("is_active")),
        "lights_on": _safe_bool(lighting_data.get("is_on")),
        "access_active": _safe_bool(access_active),
        "climate_active": _safe_bool(climate_active),

        "last_presence_at": presence_data.get("last_seen"),
        "last_motion_at": motion_data.get("last_seen"),
        "last_light_at": activity_data.get("latest_time") if _safe_bool(lighting_data.get("is_on")) else None,
        "last_access_at": None,
        "last_climate_at": activity_data.get("latest_time") if climate_active else None,
        "last_activity_at": activity_data.get("latest_time"),
        "last_seen_at": activity_data.get("latest_time"),
        "updated_at": activity_data.get("latest_time"),
    }

    # try to extract latest access signal timestamp
    access_times = []
    for item in active_access_signals + status_signals:
        if isinstance(item, dict):
            ts = item.get("time")
            if ts:
                access_times.append(ts)

    if access_times:
        normalized["last_access_at"] = max(access_times)

    # if light is off but there is no dedicated light timestamp, keep None
    # if presence is inactive but a last_seen exists, keep it for decay logic
    # same for motion

    return normalized




def _extract_announcement_text(question: str) -> Optional[str]:
    q = (question or "").strip()
    if not q:
        return None

    lower = q.lower()

    prefixes = [
        "announce ",
        "say ",
        "speak ",
        "tell the house ",
        "announce in the house ",
        "say in the house ",
        "speak in the house ",
        "announce on the desk speaker ",
        "say on the desk speaker ",
        "speak on the desk speaker ",
        "announce on desk speaker ",
        "say on desk speaker ",
        "speak on desk speaker ",
        "announce on the living speaker ",
        "say on the living speaker ",
        "speak on the living speaker ",
        "announce on the living room speaker ",
        "say on the living room speaker ",
        "speak on the living room speaker ",
        "announce on the toilet speaker ",
        "say on the toilet speaker ",
        "speak on the toilet speaker ",
        "announce on the wc speaker ",
        "say on the wc speaker ",
        "speak on the wc speaker ",
    ]

    for prefix in prefixes:
        if lower.startswith(prefix):
            text = q[len(prefix):].strip()
            if text:
                return text

    cleanup_suffixes = [
        " on the desk speaker",
        " on desk speaker",
        " on the living speaker",
        " on the living room speaker",
        " on the toilet speaker",
        " on the wc speaker",
        " in the house",
        " through the house",
        " to the house",
    ]

    cleaned = q
    cleaned_lower = lower
    for suffix in cleanup_suffixes:
        if cleaned_lower.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            cleaned_lower = cleaned.lower()

    for prefix in ["announce ", "say ", "speak ", "tell the house "]:
        if cleaned_lower.startswith(prefix):
            text = cleaned[len(prefix):].strip()
            if text:
                return text

    if " announce " in lower:
        idx = lower.find(" announce ")
        text = q[idx + len(" announce "):].strip()
        if text:
            return text

    return None


def _extract_announcement_target(question: str) -> str:
    q = (question or "").strip().lower()

    if any(x in q for x in [
        "desk speaker",
        "deskroom speaker",
        "desk room speaker",
        "on desk",
        "to desk",
        "in deskroom",
        "in the desk room",
        "to the desk room",
    ]):
        return "desk"

    if any(x in q for x in [
        "toilet speaker",
        "wc speaker",
        "on toilet",
        "to toilet",
        "in the toilet",
        "to the toilet",
        "in wc",
        "to wc",
    ]):
        return "toilet"

    if any(x in q for x in [
        "living speaker",
        "living room speaker",
        "livingroom speaker",
        "on living",
        "to living",
        "in the living room",
        "to the living room",
    ]):
        return "living"

    if any(x in q for x in [
        "party speaker",
        "party speakers",
        "party mode",
    ]):
        return "party"

    if any(x in q for x in [
        "in the house",
        "through the house",
        "to the house",
        "whole house",
        "entire house",
        "all speakers",
        "all house speakers",
    ]):
        return "living"

    return "living"


def _match_safe_action(question: str) -> Optional[Dict[str, Any]]:
    q = (question or "").strip().lower()
    if not q:
        return None

    announcement_text = _extract_announcement_text(question)
    if announcement_text:
        announcement_target = _extract_announcement_target(question)
        return {
            "type": "route",
            "target": "/tools/audio/announce",
            "params": {
                "text": announcement_text,
                "target": announcement_target,
                "level": "info",
            },
        }

    node_aliases = {
        "ai-server": ["ai-server", "aiserver", "server", "ai server"],
        "deskpi": ["deskpi", "desk pi", "deskroom pi", "desk room pi"],
        "electricpi": ["electricpi", "electric pi", "music pi", "audio pi"],
        "luifelpi": ["luifelpi", "luifel pi"],
        "discoverpi": ["discoverpi", "discover pi"],
        "attackpi": ["attackpi", "attack pi", "atticpi", "attic pi", "atticroom pi", "attack pi atticroom"],
    }

    matched_node = None
    for node_name, aliases in node_aliases.items():
        if any(alias in q for alias in aliases):
            matched_node = node_name
            break

    service_aliases = {
        "grafana": ["grafana", "grafana-server", "grafana-server.service"],
        "netdata": ["netdata", "netdata.service"],
        "meshagent": ["meshagent", "meshagent.service"],
        "ssh": ["ssh", "ssh.service"],
        "ollama": ["ollama", "ollama.service"],
        "house-agent": ["house-agent", "house agent", "house-agent.service"],
        "wake-listener": ["wake-listener", "wake listener", "wake-listener.service"],
        "flask_relays": ["flask_relays", "flask relays", "flask_relays.service"],
        "wayvnc": ["wayvnc", "wayvnc.service"],
        "wayvnc-control": ["wayvnc-control", "wayvnc control", "wayvnc-control.service"],
        "loxone-bridge": ["loxone-bridge", "loxone bridge", "loxone-bridge.service"],
        "lyrionmusicserver": ["lyrionmusicserver", "lyrion music server", "lyrionmusicserver.service"],
        "flaskmusic": ["flaskmusic", "flask music", "flaskmusic.service"],
        "relay": ["relay", "relay.service"],
        "serialflask": ["serialflask", "serial flask", "serialflask.service"],
        "flowlogger": ["flowlogger", "flow logger", "flowlogger.service"],
        "eastron": ["eastron", "eastron.service"],
        "picam-stream": ["picam-stream", "picam stream", "picam-stream.service"],
        "mediamtx": ["mediamtx", "mediamtx.service"],
        "feedback-node": ["feedback-node", "feedback node", "feedback-node.service"],
        "dnsmasq": ["dnsmasq", "dnsmasq.service"],
        "flaskapp": ["flaskapp", "flask app", "flaskapp.service"],
        "apcmonitor": ["apcmonitor", "apc monitor", "apcmonitor.service"],
        "apcupsd": ["apcupsd", "apcupsd.service"],
        "bitvavo-flask": ["bitvavo-flask", "bitvavo flask", "bitvavo-flask.service"],
        "buderuslogger": ["buderuslogger", "buderus logger", "buderuslogger.service"],
        "Eleprice": ["eleprice", "Eleprice", "eleprice.service", "Eleprice.service"],
        "sma_logger": ["sma_logger", "sma logger", "sma_logger.service"],
        "solar_logger": ["solar_logger", "solar logger", "solar_logger.service"],
        "solarpulse": ["solarpulse", "solarpulse.service"],
    }

    matched_service = None
    for service_name, aliases in service_aliases.items():
        if any(alias.lower() in q for alias in aliases):
            matched_service = service_name
            break

    if any(x in q for x in [
        "which services are down",
        "what services are down",
        "which service is down",
        "what service is down",
        "is anything broken",
        "any broken services",
        "service issues",
    ]):
        return {
            "type": "route",
            "target": "/ai/services/overview",
        }

    if any(x in q for x in [
        "which nodes have service issues",
        "which node has service issues",
        "which nodes have broken services",
        "which nodes have service warnings",
    ]):
        return {
            "type": "route",
            "target": "/ai/services/overview",
        }

    if (
        ("service" in q or "services" in q)
        and any(x in q for x in ["doing", "overview", "status", "health"])
        and matched_node is None
        and matched_service is None
    ):
        return {
            "type": "route",
            "target": "/ai/services/overview",
        }

    if (
        ("service" in q or "services" in q or "ollama" in q or "house-agent" in q)
        and any(x in q for x in ["health", "status", "running", "alive", "up"])
        and any(x in q for x in ["local", "this server", "ai-server", "on server"])
        and matched_node is None
        and matched_service is None
    ):
        return {"type": "route", "target": "/ai/service/health"}

    if (
        ("service" in q or "services" in q)
        and any(x in q for x in ["doing", "health", "status", "overview", "issues", "warnings", "running"])
        and matched_node
    ):
        return {
            "type": "route",
            "target": "/ai/service/summary",
            "params": {"node": matched_node},
        }

    if (
        ("service" in q or "services" in q)
        and any(x in q for x in ["doing", "health", "status", "overview", "issues", "warnings", "running"])
    ):
        return {
            "type": "route",
            "target": "/ai/services/overview",
        }

    if matched_service and matched_node and any(x in q for x in ["running", "active", "status", "ok", "healthy"]):
        return {
            "type": "route",
            "target": "/ai/service/summary",
            "params": {
                "node": matched_node,
                "service_hint": matched_service,
            },
        }

    if matched_service and any(x in q for x in ["running", "active", "status", "ok", "healthy"]):
        return {
            "type": "route",
            "target": "/ai/services/overview",
        }

    if (
        ("node" in q or "nodes" in q or "pis" in q or "systems" in q)
        and any(x in q for x in ["doing", "health", "status", "overview", "ok", "alive", "warnings"])
    ):
        return {"type": "route", "target": "/ai/nodes/health"}

    if matched_node and any(x in q for x in [
        "status", "health", "overloaded", "busy", "load", "ram", "cpu",
        "memory", "swap", "warning", "alarms", "doing",
    ]):
        return {
            "type": "route",
            "target": "/ai/node/summary",
            "params": {"node": matched_node},
        }

    if any(x in q for x in [
        "power now", "current power", "house power", "current consumption",
        "consumption now", "grid power", "how much power",
    ]):
        return {"type": "route", "target": "/ai/power_now"}

    if any(x in q for x in [
        "excess electricity",
        "excess energy",
        "surplus power",
        "surplus energy",
        "free electricity",
        "available solar",
        "spare solar",
        "extra solar",
        "do we have excess",
        "is there excess energy",
        "can we use extra power",
    ]):
        return {"type": "route", "target": "/ai/unified_energy_summary"}

    if any(x in q for x in [
        "which rooms are occupied",
        "what rooms are occupied",
        "which rooms are active",
        "what rooms are active",
        "occupied right now",
        "room occupancy",
        "occupancy",
        "house sensors",
        "house sensor",
        "sensor overview",
        "sensor state",
        "room activity",
        "is anyone home",
        "is anyone in the",
        "is the living room occupied",
        "is the bathroom occupied",
        "is the desk room occupied",
        "is the deskroom occupied",
        "is the entrance room occupied",
        "is the entrance occupied",
        "lights on",
        "which lights are on",
        "what lights are on",
        "active lights",
        "lighting active",
        "active motion",
        "where is motion",
        "which rooms have no clear live sensor data",
        "what rooms have no clear live sensor data",
        "which rooms have no live sensor data",
        "what rooms have no live sensor data",
        "which rooms have no sensor data",
        "what rooms have no sensor data",
        "unknown sensor rooms",
        "rooms with unknown sensor state",
        "rooms with no clear live data",
        "which rooms are idle",
        "what rooms are idle",
        "idle rooms",
        "which rooms show activity without presence",
        "what rooms show activity without presence",
        "activity without presence",
        "active without presence",
        "which rooms currently have presence detected",
        "what rooms currently have presence detected",
        "where is presence",
        "active presence",
        "which rooms have motion right now",
        "what rooms have motion right now",
        "which rooms have lights on right now",
        "what rooms have lights on right now",
        "what is happening in the",
        "what's happening in the",
        "give me the current state of the",
        "current state of the",
        "what sensors are active in the",
        "what sensors are active in ",
        "what is active in the",
        "what is active in ",
        "what is happening in the",
        "what is happening in ",
        "what's happening in the",
        "what's happening in ",
        "give me the current state of the",
        "give me the current state of ",
        "current state of the",
        "current state of ",
        "what sensors are active in the",
        "what sensors are active in ",
        "what is active in the",
        "what is active in ",
        "what is happening in the",
        "what is happening in ",
        "what's happening in the",
        "what's happening in ",
        "give me the current state of the",
        "give me the current state of ",
        "current state of the",
        "current state of ",
        "why is the",
        "why is ",
        "which room is most active",
        "what room is most active",
        "most active room",
        "most important active room",
        "which rooms are likely being used",
        "what rooms are likely being used",
        "likely human active rooms",
        "likely occupied rooms",
        "rooms likely in use",
        "which rooms are likely automation noise",
        "which rooms were recently used by a person",
        "what rooms were recently used by a person",
        "recently used by a person",
        "recent human activity",
        "which rooms had recent human activity",
        "what rooms had recent human activity",
        "rooms likely being used",
        "which rooms are likely being used",
        "what rooms are likely being used",
        "which rooms are probably being used",
        "what rooms are probably being used",
        "which room is most active",
        "what room is most active",
        "which rooms are probably just background automation",
        "what rooms are probably just background automation",
        "background automation",
        "background activity",
        "automation noise",
        "which rooms look like automation",
        "what rooms look like automation",
    ]):
        return {
            "type": "route",
            "target": "/ai/house_sensors",
            "params": {
                "minutes": 60,
                "limit": 8000,
            },
            "reason": "house_sensor_occupancy_query",
        }

    history_route = route_history_question(question)
    if history_route and history_route.get("status") == "ok" and history_route.get("target"):
        return {
            "type": "route",
            "target": history_route["target"],
            "params": history_route.get("params", {}),
            "reason": history_route.get("reason", "history_router"),
        }

    if any(x in q for x in [
        "energy today", "usage today", "used today", "today usage",
    ]):
        return {"type": "route", "target": "/ai/energy_today"}

    if any(x in q for x in [
        "energy summary", "house energy summary", "power summary",
    ]):
        return {"type": "route", "target": "/ai/energy_summary"}

    if any(x in q for x in [
        "solar", "pv", "inverter", "sma", "solar production", "how much solar",
        "grid import", "grid export", "importing from the grid", "exporting to the grid",
        "energy flow", "power flow", "house load", "house usage", "using now",
        "current house usage", "current house load", "solar vs grid",
    ]):
        return {"type": "route", "target": "/ai/unified_energy_summary"}

    if any(x in q for x in [
        "cheapest hours", "cheap electricity", "best hours to use power",
    ]):
        return {"type": "route", "target": "/ai/cheapest_hours_today"}

    if any(x in q for x in [
        "electricity price", "price now", "current electricity price", "power price",
    ]):
        return {"type": "route", "target": "/ai/electricity_price_now"}

    if any(x in q for x in [
        "salt level", "softener salt",
    ]):
        return {"type": "route", "target": "/ai/salt_tank_level"}

    if any(x in q for x in [
        "water temperature", "water temperatures",
    ]):
        return {"type": "route", "target": "/ai/water_temperatures"}

    if any(x in q for x in [
        "water softener", "softener overview",
    ]):
        return {"type": "route", "target": "/ai/water_softener_overview"}

    if any(x in q for x in [
        "pdata gas", "gas summary",
    ]):
        return {"type": "route", "target": "/ai/pdata_gas_summary"}

    if any(x in q for x in [
        "pdata overview", "full pdata overview",
    ]):
        return {"type": "route", "target": "/ai/pdata_full_overview"}

    if any(x in q for x in [
        "system health overview",
        "system overview",
        "technical overview",
        "technical house status",
        "technical status",
        "house infrastructure overview",
        "node health overview",
        "node overview",
        "which nodes have issues",
        "what nodes have issues",
        "which nodes are offline",
        "what nodes are offline",
        "monitoring overview",
        "service monitoring overview",
    ]):
        return {
            "type": "route",
            "target": "/ai/house_state",
            "params": {"summary_mode": "system"},
        }

    if any(x in q for x in [
        "house state", "house summary", "house overview",
        "house diagnostics", "house status",
        "full house state", "current house state",
    ]):
        return {
            "type": "route",
            "target": "/ai/house_state",
            "params": {"summary_mode": "overview"},
        }

    if any(x in q for x in [
        "playback state", "audio state", "voice playback state",
        "is audio playing", "is the house speaking",
    ]):
        return {"type": "route", "target": "/ai/playback_state"}

    if any(x in q for x in [
        "full status", "system status", "health status",
    ]):
        return {"type": "route", "target": "/status/full"}

    return None


def _fmt_num(value, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def _kw(value):
    try:
        return round(float(value) / 1000.0, 2)
    except Exception:
        return None


def _fmt(value, unit=""):
    try:
        return f"{round(float(value), 2)}{unit}"
    except Exception:
        return str(value)


def _human_room_label(name: str) -> str:
    if not name:
        return "unknown room"

    normalized = str(name).strip().lower().replace("-", "").replace("_", "").replace(" ", "")

    explicit = {
        "attickroom": "attic room",
        "atticroom": "attic room",
        "bathroom": "bathroom",
        "bedroom": "bedroom",
        "masterbedroom": "master bedroom",
        "childroom": "child room",
        "deskroom": "desk room",
        "livingroom": "living room",
        "diningroom": "dining room",
        "entranceroom": "entrance room",
        "hallwayroom": "hallway",
        "kitchenroom": "kitchen",
        "storageroom": "storage room",
        "powerroom": "power room",
        "gardenroom": "garden room",
        "terrasroom": "terrace",
        "wcroom": "WC",
        "toiletroom": "toilet",
        "iotroom": "IoT room",
        "trapboven": "upstairs stairs",
        "trapbeneden": "downstairs stairs",
    }

    if normalized in explicit:
        return explicit[normalized]

    cleaned = str(name).strip().replace("_", " ").replace("-", " ")
    if cleaned.lower().endswith("room"):
        cleaned = cleaned[:-4].strip() + " room"

    return " ".join(cleaned.split())


def _is_noise_room(name: str) -> bool:
    room = str(name or "").strip().lower()
    return room in {"not assigned", "unknown", ""}


def _join_natural(items):
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _summarize_service_warnings(services: dict) -> list[str]:
    warning_nodes = []
    offline_nodes = []

    for node_name, item in (services or {}).items():
        overall = str(item.get("overall_status") or "").lower()
        if overall == "warning":
            warning_nodes.append(node_name)
        elif overall in {"error", "offline", "offline_or_error"}:
            offline_nodes.append(node_name)

    parts = []
    if warning_nodes:
        parts.append(f"Some services still need attention on {_join_natural(warning_nodes)}.")
    if offline_nodes:
        parts.append(f"Service monitoring is unavailable on {_join_natural(offline_nodes)}.")
    return parts


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _room_signal_control_names(items: list, limit: int = 5) -> list[str]:
    names = []
    for item in items[:limit]:
        name = item.get("control_name")
        if name:
            name_str = str(name).replace("_", " ").strip()
            if name_str and name_str not in names:
                names.append(name_str)
    return names


def _extract_room_signals(room: dict) -> dict:
    lighting = room.get("lighting") or {}
    motion = room.get("motion") or {}
    presence = room.get("presence") or {}
    climate = room.get("climate") or {}
    access_security = room.get("access_security") or {}
    activity = room.get("activity") or {}

    active_signals = access_security.get("active_signals") or []
    status_signals = access_security.get("status_signals") or []
    alert_signals = access_security.get("alert_signals") or []

    binary_on_count = _safe_int(activity.get("binary_on_count"), 0)
    telemetry_count = _safe_int(activity.get("telemetry_count"), 0)

    temp_actual = _safe_float(climate.get("temperature_actual"))
    temp_target = _safe_float(climate.get("temperature_target"))
    humidity = _safe_float(climate.get("humidity"))
    co2 = _safe_float(climate.get("co2"))
    open_window = climate.get("open_window")

    presence_on = _safe_bool(presence.get("is_active"))
    motion_on = _safe_bool(motion.get("is_active"))
    lights_on = _safe_bool(lighting.get("is_on"))

    access_on = len(active_signals) > 0 or len(status_signals) > 0
    security_on = len(alert_signals) > 0
    climate_on = any(v is not None for v in [temp_actual, temp_target, humidity, co2, open_window])
    generic_activity_on = binary_on_count > 0 or telemetry_count > 0 or str(room.get("room_status") or "").strip().lower() == "active_no_presence"

    return {
        "presence": presence_on,
        "motion": motion_on,
        "access": access_on,
        "security": security_on,
        "lighting": lights_on,
        "climate": climate_on,
        "generic_activity": generic_activity_on,
        "binary_on_count": binary_on_count,
        "telemetry_count": telemetry_count,
        "temp_actual": temp_actual,
        "temp_target": temp_target,
        "humidity": humidity,
        "co2": co2,
        "open_window": open_window,
        "active_signal_names": _room_signal_control_names(active_signals, limit=5),
        "status_signal_names": _room_signal_control_names(status_signals, limit=5),
        "alert_signal_names": _room_signal_control_names(alert_signals, limit=5),
    }


_REASON_PRIORITY = [
    "presence",
    "motion",
    "access",
    "security",
    "lighting",
    "climate",
    "generic_activity",
]


def _infer_activity_reason(signals: dict) -> dict:
    active_reasons = [reason for reason in _REASON_PRIORITY if signals.get(reason)]

    if not active_reasons:
        return {
            "is_active": False,
            "primary_reason": None,
            "secondary_reasons": [],
            "confidence": "low",
        }

    primary = active_reasons[0]
    secondary = active_reasons[1:]

    if primary in {"presence", "motion"}:
        confidence = "high"
    elif primary in {"access", "security", "lighting", "climate"}:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "is_active": True,
        "primary_reason": primary,
        "secondary_reasons": secondary,
        "confidence": confidence,
    }


def _build_reason_code(primary: Optional[str], secondary: list[str]) -> str:
    if not primary:
        return "inactive"
    if secondary:
        return f"{primary}_with_" + "_and_".join(secondary[:3])
    return primary


def _build_reason_details(signals: dict, primary: Optional[str], secondary: list[str]) -> list[str]:
    details = []

    if signals.get("presence"):
        details.append("Presence is currently active.")
    else:
        details.append("Presence is not currently active.")

    if signals.get("motion"):
        details.append("Motion is currently active.")
    else:
        details.append("Motion is not currently active.")

    if signals.get("lighting"):
        details.append("Lighting is currently on.")
    else:
        details.append("Lighting is currently off.")

    access_names = signals.get("active_signal_names") or []
    status_names = signals.get("status_signal_names") or []
    alert_names = signals.get("alert_signal_names") or []

    if access_names or status_names:
        combined = []
        for name in access_names + status_names:
            if name not in combined:
                combined.append(name)
        details.append(f"Access-related signals include {_join_natural(combined[:5])}.")

    if alert_names:
        details.append(f"Security-related alerts include {_join_natural(alert_names[:5])}.")

    climate_bits = []
    if signals.get("temp_actual") is not None:
        climate_bits.append(f"temperature is {round(float(signals['temp_actual']), 1)} degrees")
    if signals.get("temp_target") is not None:
        climate_bits.append(f"target is {round(float(signals['temp_target']), 1)} degrees")
    if signals.get("humidity") is not None:
        climate_bits.append(f"humidity is {round(float(signals['humidity']), 1)} percent")
    if signals.get("co2") is not None:
        climate_bits.append(f"CO2 is {round(float(signals['co2']), 1)}")
    if signals.get("open_window") is not None:
        climate_bits.append(f"window is {'open' if bool(signals.get('open_window')) else 'closed'}")

    if climate_bits:
        details.append("Climate data: " + ", ".join(climate_bits) + ".")

    binary_on_count = _safe_int(signals.get("binary_on_count"), 0)
    telemetry_count = _safe_int(signals.get("telemetry_count"), 0)
    if binary_on_count or telemetry_count:
        details.append(
            f"Additional room state includes {binary_on_count} active binary items and {telemetry_count} telemetry items."
        )

    if primary and secondary:
        details.append(
            f"Primary cause is {primary}; supporting signals include {_join_natural(secondary[:4])}."
        )

    return details


def _build_primary_reason_summary(room_name: str, signals: dict, reason: dict) -> str:
    primary = reason.get("primary_reason")
    no_presence = not signals.get("presence")
    no_motion = not signals.get("motion")

    if primary == "presence":
        if signals.get("motion"):
            return f"The {room_name} is active because presence is currently detected, with motion also indicating recent activity."
        return f"The {room_name} is active because presence is currently detected."

    if primary == "motion":
        if no_presence:
            return f"The {room_name} is active due to motion, but no presence is currently detected."
        return f"The {room_name} is active due to motion."

    if primary == "access":
        if no_presence and no_motion:
            return f"The {room_name} is active due to recent access-related signals, but no presence or motion is currently detected."
        return f"The {room_name} is active due to access-related state changes."

    if primary == "security":
        return f"The {room_name} is active because a security-related state is currently active."

    if primary == "lighting":
        if no_presence and no_motion:
            return f"The {room_name} appears active mainly because lights are on, without confirmed presence or motion."
        return f"The {room_name} is active with lighting currently on."

    if primary == "climate":
        if no_presence and no_motion:
            return f"The {room_name} shows activity mainly from climate-related state changes, without signs of occupancy."
        return f"The {room_name} is active with climate-related state changes."

    if primary == "generic_activity":
        if no_presence and no_motion:
            return f"The {room_name} is active from general room state changes, but no stronger cause is currently visible."
        return f"The {room_name} is active from general room state changes."

    return f"The {room_name} currently appears inactive."


def _analyze_room_activity_reason(room_name, room_payload, now_ts=None):
    """
    Human-readable explanation of why a room looks active.
    Works with the real nested /ai/house_sensors payload.
    """
    normalized = _extract_room_signal_snapshot(room_name, room_payload)
    profile = _get_room_role_profile(room_name, normalized)
    recency = _build_room_recency_snapshot(room_name, normalized, now_ts=now_ts)

    presence = _safe_bool(normalized.get("presence"))
    motion = _safe_bool(normalized.get("motion"))
    lights_on = _safe_bool(normalized.get("lights_on"))
    access_active = _safe_bool(normalized.get("access_active"))
    climate_active = _safe_bool(normalized.get("climate_active"))

    reasons = []
    primary = "unknown"
    secondary = None
    confidence = "low"

    if presence:
        primary = "presence_detected"
        confidence = "high"
        reasons.append("presence is currently detected")

        if motion:
            secondary = "motion_detected"
            reasons.append("motion is also active")

        if lights_on:
            reasons.append("lights are on")

    elif motion:
        if recency["motion_recency_band"] == "fresh":
            primary = "recent_motion"
            confidence = "medium"
            reasons.append("recent motion suggests recent human activity")
        else:
            primary = "stale_motion"
            confidence = "low"
            reasons.append("motion was seen earlier, but it is no longer very recent")

        if lights_on:
            secondary = "lights_on"
            reasons.append("lights remain on")

    elif access_active:
        primary = "access_triggered"
        confidence = "low"
        reasons.append("there was an access-related trigger")
        reasons.append("access alone is not strong proof of ongoing presence")

        if lights_on:
            secondary = "lights_on"
            reasons.append("lights remain on after access activity")

    elif lights_on:
        primary = "lights_only"
        confidence = "low"
        reasons.append("lights are on without stronger live human signals")

    elif climate_active:
        primary = "background_automation"
        confidence = "low"
        reasons.append("climate or automation activity is present")
        reasons.append("this looks more like background system behavior")

    else:
        if recency["presence_recency_band"] == "fresh":
            primary = "recent_presence_memory"
            confidence = "medium"
            reasons.append("this room had recent strong presence memory")
        elif recency["motion_recency_band"] in {"fresh", "aging"}:
            primary = "recent_motion_memory"
            confidence = "low"
            reasons.append("this room had recent motion memory")
        else:
            primary = "idle"
            confidence = "low"
            reasons.append("no strong activity signals are currently active")

    if profile["role"] in {"transitional", "bathroom", "utility"} and primary in {
        "recent_motion",
        "stale_motion",
        "lights_only",
        "access_triggered",
        "recent_motion_memory",
    }:
        reasons.append(f"{profile['role']} rooms should decay faster than true occupied rooms")

    return {
        "activity_reason": "; ".join(reasons),
        "activity_reason_primary": primary,
        "activity_reason_secondary": secondary,
        "activity_reason_confidence": confidence,
    }



def _get_room_activity_reason(room: dict) -> dict:
    existing = room.get("activity_reason")
    if isinstance(existing, dict) and existing:
        return existing

    analysis = _analyze_room_activity_reason(room)
    return analysis.get("activity_reason", {})






def _summarize_house_state(data: dict, action: dict) -> str:
    params = (action or {}).get("params") or {}
    summary_mode = str(params.get("summary_mode") or "overview").strip().lower()

    if summary_mode not in {"overview", "briefing", "system"}:
        summary_mode = "overview"

    try:
        summary_text = summarize_house_state(data, mode=summary_mode)
        if summary_text:
            return summary_text
    except Exception:
        pass

    summary = data.get("summary", {}) or {}
    interpreted_house_load_kw = summary.get("interpreted_house_load_kw")
    power_watts = summary.get("current_power_watts")

    if interpreted_house_load_kw is not None:
        try:
            if summary_mode == "system":
                offline_nodes = summary.get("offline_nodes") or []
                warning_nodes_count = summary.get("warning_nodes_count")
                service_warning_hosts = summary.get("service_warning_hosts") or []
                monitoring_unavailable_nodes = summary.get("monitoring_unavailable_nodes") or []

                parts = [
                    f"Current interpreted house load is {round(float(interpreted_house_load_kw), 2)} kilowatts."
                ]
                if offline_nodes:
                    parts.append(f"Offline nodes: {', '.join(offline_nodes)}.")
                if warning_nodes_count:
                    parts.append(f"Nodes with warnings: {warning_nodes_count}.")
                if service_warning_hosts:
                    parts.append(f"Service warnings are present on: {', '.join(service_warning_hosts)}.")
                if monitoring_unavailable_nodes:
                    parts.append(f"Service monitoring is unavailable on: {', '.join(monitoring_unavailable_nodes)}.")
                return " ".join(parts)

            return f"The house is currently using {round(float(interpreted_house_load_kw), 2)} kilowatts."
        except Exception:
            return "The house state is available, but the summary could not be fully rendered."

    if power_watts is not None:
        try:
            kw = round(abs(float(power_watts)) / 1000.0, 2)
            return f"The house is currently using about {kw} kilowatts."
        except Exception:
            return "The house state is available, but the summary could not be fully rendered."

    return "The house state is available, but no concise overview could be generated."







def _summarize_history_presence(data: dict, action: dict) -> str:
    items = data.get("items", []) or []
    room = (action.get("params") or {}).get("room") or "the house"
    minutes = (action.get("params") or {}).get("minutes", data.get("minutes", 60))

    active_items = [i for i in items if i.get("state_key") == "active" and i.get("is_active") is True]
    event_items = [i for i in items if i.get("state_key") == "events"]
    latest_time = None

    for item in items:
        t = item.get("time")
        if t and (latest_time is None or t > latest_time):
            latest_time = t

    if active_items:
        return (
            f"Yes, I found motion or presence in {room} within the last {minutes} minutes. "
            f"There are {len(active_items)} active presence states. "
            f"Latest activity was at {latest_time or 'an unknown time'}."
        )

    if event_items:
        return (
            f"I found recent motion or presence events in {room} within the last {minutes} minutes, "
            f"but nothing is currently marked active. Latest event was at {latest_time or 'an unknown time'}."
        )

    return f"I found no motion or presence in {room} within the last {minutes} minutes."


def _summarize_history_binary_active(data: dict, action: dict) -> str:
    items = data.get("items", []) or []
    room = (action.get("params") or {}).get("room") or "the house"
    minutes = (action.get("params") or {}).get("minutes", data.get("minutes", 60))

    filtered = []
    skip_state_keys = {
        "activeSince", "time", "min", "max", "step", "nextEntryTime",
        "prepareDuration", "ringDuration", "snoozeDuration",
    }

    for item in items:
        state_key = str(item.get("state_key") or "")
        value = item.get("value")
        if state_key in skip_state_keys:
            continue
        if value in (None, 0, 0.0, False):
            continue
        filtered.append(item)

    if not filtered:
        return f"I found nothing currently active in {room} over the last {minutes} minutes."

    preview = []
    for item in filtered[:5]:
        control_name = item.get("control_name") or "unknown control"
        state_key = item.get("state_key") or "value"
        value = item.get("value")
        preview.append(f"{control_name} ({state_key}={value})")

    return (
        f"I found {len(filtered)} currently active binary states in {room} over the last {minutes} minutes. "
        f"Examples: {'; '.join(preview)}."
    )


def _summarize_history_binary_changes(data: dict, action: dict) -> str:
    items = data.get("items", []) or []
    room = (action.get("params") or {}).get("room") or "the house"
    minutes = (action.get("params") or {}).get("minutes", data.get("minutes", 60))

    if not items:
        return f"I found no recent binary changes in {room} over the last {minutes} minutes."

    preview = []
    for item in items[:5]:
        control_name = item.get("control_name") or "unknown control"
        state_key = item.get("state_key") or "value"
        current_value = item.get("current_value")
        previous_value = item.get("previous_value")
        last_time = item.get("last_time") or item.get("first_time") or "unknown time"
        change_count = item.get("change_count", 0)

        if previous_value is None:
            preview.append(
                f"{control_name} ({state_key} now {current_value} at {last_time}, samples={item.get('samples', 0)})"
            )
        else:
            preview.append(
                f"{control_name} ({state_key}: {previous_value} -> {current_value} at {last_time}, changes={change_count})"
            )

    return (
        f"I found {len(items)} recent binary changes in {room} over the last {minutes} minutes. "
        f"Examples: {'; '.join(preview)}."
    )


def _summarize_history_telemetry(data: dict, action: dict) -> str:
    items = data.get("items", []) or []
    room = (action.get("params") or {}).get("room")
    minutes = (action.get("params") or {}).get("minutes", data.get("minutes", 120))
    scope = room or "the house"

    climate_items = []
    for item in items:
        state_key = str(item.get("state_key") or "").lower()
        sensor_type = str(item.get("sensor_type") or "").lower()
        domain = str(item.get("domain") or "").lower()

        if state_key in {"tempactual", "humidityactual"}:
            climate_items.append(item)
            continue

        if sensor_type == "climate_controller" and state_key in {"tempactual", "humidityactual"}:
            climate_items.append(item)
            continue

        if domain == "climate" and state_key in {"tempactual", "humidityactual"}:
            climate_items.append(item)

    if not climate_items:
        return f"I found no recent temperature or humidity telemetry for {scope} in the last {minutes} minutes."

    latest_by_room_and_key = {}
    for item in climate_items:
        key = (item.get("room") or "unknown", item.get("state_key"))
        current_time = item.get("time") or ""
        old = latest_by_room_and_key.get(key)
        if old is None or current_time > (old.get("time") or ""):
            latest_by_room_and_key[key] = item

    grouped = {}
    for (room_name, _), item in latest_by_room_and_key.items():
        grouped.setdefault(room_name, {})
        grouped[room_name][item.get("state_key")] = item.get("value")

    preview = []
    for room_name in sorted(grouped.keys())[:8]:
        temp = grouped[room_name].get("tempActual")
        hum = grouped[room_name].get("humidityActual")

        parts = [room_name]
        if temp is not None:
            parts.append(f"temp {round(float(temp), 1)} C")
        if hum is not None:
            parts.append(f"humidity {round(float(hum), 1)} percent")

        if len(parts) > 1:
            preview.append(", ".join(parts))

    if not preview:
        return f"I found no recent temperature or humidity telemetry for {scope} in the last {minutes} minutes."

    return (
        f"I found recent house climate telemetry for {len(grouped)} rooms in {scope} "
        f"over the last {minutes} minutes. {'; '.join(preview)}."
    )


def _summarize_history_room_activity(data: dict, action: dict) -> str:
    items = data.get("items", []) or []
    room = (action.get("params") or {}).get("room")
    minutes = (action.get("params") or {}).get("minutes", data.get("minutes", 60))
    room_count = int(data.get("room_count", len(items)))

    if not items:
        if room:
            return f"I found no room activity summary for {room} in the last {minutes} minutes."
        return f"I found no room activity in the last {minutes} minutes."

    def score_item(item: dict) -> tuple:
        room_name = str(item.get("room") or "")
        if _is_noise_room(room_name):
            room_penalty = -100
        else:
            room_penalty = 0

        on_items = item.get("on_items", []) or []

        presence_count = 0
        access_count = 0
        security_count = 0
        heating_count = 0
        power_count = 0
        other_count = 0

        for sub in on_items:
            domain = str(sub.get("domain") or "").lower()
            control_name = str(sub.get("control_name") or "").lower()

            if domain == "presence":
                presence_count += 1
            elif domain == "access":
                access_count += 1
            elif domain == "security":
                security_count += 1
            elif domain == "heating":
                heating_count += 1
            elif domain == "power":
                if any(x in control_name for x in ["picore", "psu_switch", "power_switch"]):
                    power_count += 1
                else:
                    other_count += 1
            else:
                other_count += 1

        activity_score = (
            presence_count * 100
            + access_count * 60
            + security_count * 50
            + heating_count * 20
            + other_count * 15
            + max(0, item.get("binary_on_count", 0) - power_count) * 10
            + item.get("telemetry_count", 0) * 0.1
            + room_penalty
        )

        return (
            activity_score,
            presence_count,
            access_count,
            security_count,
            item.get("binary_on_count", 0),
            item.get("telemetry_count", 0),
        )

    filtered_items = []
    for item in items:
        room_name = str(item.get("room") or "")
        if _is_noise_room(room_name):
            continue
        filtered_items.append(item)

    if room:
        first = filtered_items[0] if filtered_items else items[0]
        active_count = first.get("binary_on_count", 0)
        state_count = first.get("binary_state_count", 0)
        latest_time = first.get("latest_time") or "unknown time"

        presence_now = 0
        on_items = first.get("on_items", []) or []
        for sub in on_items:
            if str(sub.get("domain") or "").lower() == "presence":
                presence_now += 1

        if presence_now > 0:
            return (
                f"I summarized activity for {_human_room_label(room)} over the last {minutes} minutes. "
                f"There is active presence there now. "
                f"It has {active_count} active items out of {state_count} tracked binary states. "
                f"Latest activity was at {latest_time}."
            )

        return (
            f"I summarized activity for {_human_room_label(room)} over the last {minutes} minutes. "
            f"It has {active_count} active items out of {state_count} tracked binary states. "
            f"Latest activity was at {latest_time}."
        )

    ranked = sorted(filtered_items, key=score_item, reverse=True)
    top_rooms = [_human_room_label(item.get("room")) for item in ranked[:5]]

    active_presence_rooms = []
    for item in ranked:
        room_name = item.get("room")
        on_items = item.get("on_items", []) or []
        if any(str(sub.get("domain") or "").lower() == "presence" for sub in on_items):
            active_presence_rooms.append(_human_room_label(room_name))

    active_presence_rooms = active_presence_rooms[:5]

    parts = [
        f"I summarized room activity for {room_count} rooms over the last {minutes} minutes."
    ]

    if top_rooms:
        parts.append(f"Most active rooms were {_join_natural(top_rooms)}.")

    if active_presence_rooms:
        parts.append(f"Active presence is currently detected in {_join_natural(active_presence_rooms)}.")

    return " ".join(parts)


def _summarize_history_last_change(data: dict, action: dict) -> str:
    controls_count = int(data.get("controls_count", 0))
    rooms_count = int(data.get("rooms_count", 0))
    minutes = (action.get("params") or {}).get("minutes", data.get("minutes", 60))

    if controls_count == 0:
        return f"I found no recent last-change data in the last {minutes} minutes."

    return (
        f"I found last-change information for {controls_count} controls across "
        f"{rooms_count} rooms in the last {minutes} minutes."
    )


def _summarize_node_health(data: dict) -> str:
    payload = data.get("data", {}) if isinstance(data, dict) else {}
    if not isinstance(payload, dict) or not payload:
        return "I could not read any node health data."

    total = len(payload)
    warning_nodes = []
    offline_nodes = []
    top_cpu = None
    top_ram = None
    top_load = None

    for node, info in payload.items():
        status = info.get("status", "unknown")

        if status == "warning":
            warning_nodes.append(node)
        elif status != "ok":
            offline_nodes.append(node)

        cpu = info.get("cpu_total_percent")
        ram = info.get("ram_used_percent")
        load1 = info.get("load1")

        if cpu is not None:
            if top_cpu is None or float(cpu) > float(top_cpu[1]):
                top_cpu = (node, cpu)

        if ram is not None:
            if top_ram is None or float(ram) > float(top_ram[1]):
                top_ram = (node, ram)

        if load1 is not None:
            if top_load is None or float(load1) > float(top_load[1]):
                top_load = (node, load1)

    parts = [f"I checked {total} monitored nodes."]

    if offline_nodes:
        parts.append(f"Unreachable or error nodes: {', '.join(offline_nodes)}.")
    if warning_nodes:
        parts.append(f"Warning state nodes: {', '.join(warning_nodes)}.")
    if not offline_nodes and not warning_nodes:
        parts.append("All nodes are reachable and currently report ok status.")

    if top_cpu is not None:
        parts.append(f"Highest CPU is {top_cpu[0]} at {round(float(top_cpu[1]), 2)} percent.")
    if top_ram is not None:
        parts.append(f"Highest RAM usage is {top_ram[0]} at {round(float(top_ram[1]), 2)} percent.")
    if top_load is not None:
        parts.append(f"Highest load is {top_load[0]} at {round(float(top_load[1]), 2)}.")

    return " ".join(parts)


def _summarize_node_summary(data: dict, question: str = "") -> str:
    payload = data.get("data", {}) if isinstance(data, dict) else {}
    if not isinstance(payload, dict) or not payload:
        return "I could not read node summary data."

    node = payload.get("hostname") or payload.get("node") or "This node"
    cpu = payload.get("cpu_total_percent")
    ram = payload.get("ram_used_percent")
    load1 = payload.get("load1")
    alarms = payload.get("active_alarm_count", 0)
    warnings = payload.get("warnings", []) or []

    q = (question or "").lower()

    if "overload" in q or "overloaded" in q or "busy" in q:
        overloaded = False
        reasons = []

        if cpu is not None and float(cpu) >= 80:
            overloaded = True
            reasons.append(f"CPU is high at {round(float(cpu), 2)} percent")
        if ram is not None and float(ram) >= 85:
            overloaded = True
            reasons.append(f"RAM usage is high at {round(float(ram), 2)} percent")
        if load1 is not None and float(load1) >= 2.0:
            reasons.append(f"load is {round(float(load1), 2)}")

        if alarms and int(alarms) > 0:
            overloaded = True
            reasons.append(f"{alarms} active alarms")

        if warnings:
            reasons.append(f"warnings: {', '.join(warnings)}")

        if overloaded:
            return f"{node} does look stressed right now. " + ". ".join(reasons) + "."
        return (
            f"{node} does not look overloaded right now. "
            f"CPU is {round(float(cpu), 2) if cpu is not None else 'unknown'} percent, "
            f"RAM is {round(float(ram), 2) if ram is not None else 'unknown'} percent, "
            f"load is {round(float(load1), 2) if load1 is not None else 'unknown'}, "
            f"active alarms are {alarms}, "
            f"and warnings are {', '.join(warnings) if warnings else 'none'}."
        )

    if warnings:
        return (
            f"{node} is reporting warning status. "
            f"Warnings detected: {', '.join(warnings)}. "
            f"CPU is {round(float(cpu), 2) if cpu is not None else 'unknown'} percent, "
            f"RAM usage is {round(float(ram), 2) if ram is not None else 'unknown'} percent, "
            f"load is {round(float(load1), 2) if load1 is not None else 'unknown'}, "
            f"and active alarms are {alarms}."
        )

    return (
        f"{node} is reporting {payload.get('health_status', 'ok')} status. "
        f"CPU is {round(float(cpu), 2) if cpu is not None else 'unknown'} percent, "
        f"RAM usage is {round(float(ram), 2) if ram is not None else 'unknown'} percent, "
        f"load is {round(float(load1), 2) if load1 is not None else 'unknown'}, "
        f"and active alarms are {alarms}."
    )


def _build_answer_from_safe_result(action, result, question: str = ""):
    if result.get("status") != "ok":
        return "I could not complete that request."

    data = result.get("data", {}) or {}
    target = action.get("target", "")

    if target == "/ai/nodes/health":
        return _summarize_node_health(data)

    if target == "/ai/node/summary":
        return _summarize_node_summary(data, question=question)

    if target == "/ai/node/alerts":
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        alarms = payload.get("alarms", {}) if isinstance(payload, dict) else {}
        active = []
        for _, alarm in alarms.items():
            if alarm.get("status") in ("WARNING", "CRITICAL"):
                active.append(alarm)

        if not active:
            return "There are no active node alerts."
        return f"I found {len(active)} active node alerts."

    if target == "/ai/house_state_summary":
        room_count = data.get("room_count", 0)
        error_count = data.get("error_count", 0)
        return f"I retrieved the current house state summary for {room_count} rooms with {error_count} errors."

    if target == "/ai/house_state":
        return _summarize_house_state(data, action)

    if target == "/ai/house_sensors":
        return _summarize_house_sensors(data, action, question=question)

    if target == "/ai/playback_state":
        effective = data.get("effective", {}) if isinstance(data, dict) else {}
        audio_state = data.get("audio_state", {}) if isinstance(data, dict) else {}
        conversation_state = data.get("conversation_state", {}) if isinstance(data, dict) else {}

        if effective.get("active"):
            room = effective.get("effective_target_room") or "unknown room"
            player = effective.get("effective_target_player") or "unknown player"
            source = effective.get("source") or "unknown source"
            return f"Playback is active in {room} on player {player}. Source is {source}. Wake suppression is enabled."

        if effective.get("suppress_wake"):
            return "Playback is not active, but wake suppression is still enabled during cooldown."

        if audio_state.get("is_playing"):
            target_name = audio_state.get("active_target") or "unknown target"
            player = audio_state.get("active_player_id") or "unknown player"
            return f"Audio is currently playing on {target_name} using player {player}."

        if conversation_state.get("active"):
            room = conversation_state.get("target_room") or "unknown room"
            return f"The conversation manager still shows active playback context for {room}, but no direct audio playback is active."

        return "No audio playback is active and wake suppression is not enabled."

    if target == "/ai/loxone_history_presence_ai":
        return _summarize_history_presence(data, action)

    if target == "/ai/loxone_history_binary_active":
        return _summarize_history_binary_active(data, action)

    if target == "/ai/loxone_history_binary_changes":
        return _summarize_history_binary_changes(data, action)

    if target == "/ai/loxone_history_telemetry_latest":
        return _summarize_history_telemetry(data, action)

    if target == "/ai/loxone_history_room_activity_ai":
        return _summarize_history_room_activity(data, action)

    if target == "/ai/loxone_history_last_change":
        return _summarize_history_last_change(data, action)

    if target == "/ai/power_now":
        watts = data.get("power_watts")
        if watts:
            return f"The house is currently using {_fmt(_kw(watts), ' kilowatts')}."
        return "I could not read the current power."

    if target == "/ai/sma_summary":
        power = data.get("power_watts") or data.get("ac_power")
        daily = data.get("daily_energy")
        parts = []
        if power:
            parts.append(f"{_fmt(_kw(power), ' kilowatts')} right now")
        if daily:
            parts.append(f"{_fmt(daily, ' kilowatt hours today')}")
        if parts:
            return "Solar is producing " + " and ".join(parts) + "."
        return "I could not read the solar data."

    if target == "/ai/electricity_price_now":
        price = data.get("price")
        if price:
            return f"Electricity currently costs {_fmt(price, ' euro per kilowatt hour')}."
        return "I could not read the electricity price."

    if target == "/ai/unified_energy_summary":
        structured = data.get("structured", {})
        solar = structured.get("solar_power_kw")
        grid_in = structured.get("grid_import_kw")
        grid_out = structured.get("grid_export_kw")
        load = structured.get("estimated_house_load_kw")
        net_grid = structured.get("net_grid_kw")

        q = (question or "").lower()

        if any(x in q for x in ["solar", "pv", "inverter", "sma", "solar production"]):
            if solar is not None:
                return f"Solar is currently producing {_fmt(solar, ' kilowatts')}."
            return "I could not read current solar production."

        if any(x in q for x in ["grid", "import", "export", "importing from the grid", "exporting to the grid"]):
            if grid_out is not None and float(grid_out) > 0:
                return f"The house is currently exporting {_fmt(grid_out, ' kilowatts')} to the grid."
            if grid_in is not None:
                return f"The house is currently importing {_fmt(grid_in, ' kilowatts')} from the grid."
            if net_grid is not None:
                return f"Net grid flow is currently {_fmt(net_grid, ' kilowatts')}."
            return "I could not read the current grid flow."

        if any(x in q for x in ["house load", "house usage", "using now", "current house usage", "current house load", "load"]):
            if load is not None:
                return f"The estimated house load is {_fmt(load, ' kilowatts')} right now."
            return "I could not read the current house load."

        answer = data.get("answer")
        if answer:
            return answer

        if load is not None:
            return (
                f"The house is using {_fmt(load, ' kilowatts')} right now, "
                f"solar is producing {_fmt(solar, ' kilowatts')}, "
                f"grid import is {_fmt(grid_in, ' kilowatts')}, "
                f"and grid export is {_fmt(grid_out, ' kilowatts')}."
            )

        return "I could not build the unified energy summary."

    if target == "/ai/energy_summary":
        power = data.get("power_watts")
        if power:
            return f"The house is using {_fmt(_kw(power), ' kilowatts')} right now."
        return "Energy data is available but incomplete."

    if target == "/ai/energy_today":
        return "Today's energy usage data has been retrieved."

    if target == "/ai/water_temperatures":
        t1 = data.get("temp1")
        t2 = data.get("temp2")
        if t1 and t2:
            return f"Water temperatures are {_fmt(t1, ' degrees')} and {_fmt(t2, ' degrees')}."
        return "Water temperature data is available."

    if target == "/ai/salt_tank_level":
        level = data.get("level_percent")
        if level:
            return f"The salt tank is at {_fmt(level, ' percent')}."
        return "Salt level data is available."

    if target == "/house/status":
        return "The house systems are running normally."

    if target == "/status/full":
        return "All systems are operational."

    if target == "/ai/service/summary":
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        if not isinstance(payload, dict) or not payload:
            return "I could not read service summary data."

        node = payload.get("node", "unknown node")
        overall = payload.get("overall_status", "unknown")
        services = payload.get("services", []) or []

        params = action.get("params", {}) or {}
        service_hint = params.get("service_hint")

        if service_hint:
            normalized_hint = str(service_hint).lower()
            matched = None
            for service in services:
                service_name = str(service.get("service", "")).lower()
                if normalized_hint in service_name:
                    matched = service
                    break

            if matched:
                service_name = matched.get("service", service_hint)
                status = matched.get("status", "unknown")
                if status == "active":
                    return f"{service_name} on {node} is active."
                return f"{service_name} on {node} is {status}."

            return f"I checked {node}, but I could not find a monitored service matching {service_hint}."

        active_count = sum(1 for s in services if s.get("status") == "active")
        non_active = [s for s in services if s.get("status") != "active"]

        if non_active:
            preview = ", ".join(
                f"{s.get('service')}: {s.get('status')}"
                for s in non_active[:5]
            )
            return (
                f"{node} service health is {overall}. "
                f"{active_count} services are active. "
                f"Services needing attention: {preview}."
            )

        return (
            f"{node} service health is {overall}. "
            f"All {active_count} monitored services are active."
        )

    if target == "/ai/services/overview":
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        if not isinstance(payload, dict) or not payload:
            return "I could not read service overview data."

        q = (question or "").lower()
        total_nodes = len(payload)
        nodes_with_issues = []
        down_services = []

        for node_name, node_info in payload.items():
            services = node_info.get("services", []) or []
            overall = node_info.get("overall_status", "unknown")

            node_bad = []
            for item in services:
                service_name = item.get("service", "unknown service")
                status = item.get("status", "unknown")

                if status != "active":
                    node_bad.append(f"{service_name} ({status})")
                    down_services.append(f"{node_name}: {service_name} ({status})")

            if overall != "ok" or node_bad:
                if node_bad:
                    nodes_with_issues.append(f"{node_name}: {', '.join(node_bad[:4])}")
                else:
                    nodes_with_issues.append(f"{node_name}: overall status {overall}")

        if any(x in q for x in [
            "which services are down",
            "what services are down",
            "which service is down",
            "what service is down",
            "is anything broken",
            "any broken services",
            "service issues",
        ]):
            if not down_services:
                return f"I checked service health on {total_nodes} nodes. No monitored services are down."
            return (
                f"I found service issues on {len(nodes_with_issues)} nodes. "
                f"Affected services: {'; '.join(down_services[:10])}."
            )

        if any(x in q for x in [
            "which nodes have service issues",
            "which node has service issues",
            "which nodes have broken services",
            "which nodes have service warnings",
        ]):
            if not nodes_with_issues:
                return f"I checked service health on {total_nodes} nodes. No nodes currently have service issues."
            return (
                f"I found service issues on {len(nodes_with_issues)} nodes. "
                f"Details: {'; '.join(nodes_with_issues[:6])}."
            )

        if not nodes_with_issues:
            return (
                f"I checked service health on {total_nodes} nodes. "
                f"All monitored service nodes report ok status."
            )

        return (
            f"I checked service health on {total_nodes} nodes. "
            f"Nodes with service issues: {'; '.join(nodes_with_issues[:6])}."
        )

    if target == "/ai/service/health":
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        if not isinstance(payload, dict) or not payload:
            return "I could not read local service health."

        overall = payload.get("overall_status", "unknown")
        node = payload.get("node", "local system")
        services = payload.get("services", []) or []

        if not services:
            return f"{node} service health is {overall}, but no monitored services were returned."

        active_count = 0
        non_active = []

        for item in services:
            service_name = item.get("service", "unknown service")
            status = item.get("status", "unknown")
            if status == "active":
                active_count += 1
            else:
                non_active.append(f"{service_name}: {status}")

        if non_active:
            return (
                f"{node} service health is {overall}. "
                f"{active_count} services are active. "
                f"Services with issues: {'; '.join(non_active)}."
            )

        return (
            f"{node} service health is {overall}. "
            f"All {len(services)} monitored services are active."
        )

    return "I found some data, but I could not summarize it yet."


def handle_house_or_ai_question(question: str) -> Dict[str, Any]:
    action = _match_safe_action(question)
    if action:
        auth_result = classify_action_auth(action)

        if auth_result.get("allowed") is True:
            exec_result = execute_safe_action(action)

            if (
                action.get("target") == "/ai/house_sensors"
                and isinstance(exec_result, dict)
                and exec_result.get("status") == "ok"
            ):
                payload = exec_result.get("data")
                if isinstance(payload, dict):
                    exec_result["data"] = _enrich_house_sensor_payload_with_activity_reasons(payload)

            answer = _build_answer_from_safe_result(action, exec_result, question=question)
            return {
                "status": "ok" if exec_result.get("status") == "ok" else exec_result.get("status", "error"),
                "mode": "safe_executor",
                "intents": ["safe_executor"],
                "used_tools": [],
                "tool_data": {
                    "safe_executor": {
                        "action": action,
                        "result": exec_result,
                    },
                    "auth_policy": auth_result,
                },
                "answer": answer,
                "auth_result": auth_result,
                "executor_action": action,
                "executor_result": exec_result,
            }

        if auth_result.get("auth_level") == "approval_required":
            approval = get_pending_approval_service().create_request(
                action=action,
                auth_level=auth_result.get("auth_level"),
                approval_method=auth_result.get("approval_method"),
                question=question,
                room_id=(action.get("params") or {}).get("room"),
                requested_by="agent_query",
                expires_in_seconds=90,
            )
            return {
                "status": "ok",
                "mode": "approval_required",
                "intents": ["approval_required"],
                "used_tools": [],
                "tool_data": {
                    "auth_policy": auth_result,
                    "approval": approval,
                },
                "answer": (
                    f"This action requires approval before execution. "
                    f"Approval token: {approval.get('token')}."
                ),
                "auth_result": auth_result,
                "approval": approval,
                "executor_action": action,
            }

        return {
            "status": "blocked",
            "mode": "policy_blocked",
            "intents": ["policy_blocked"],
            "used_tools": [],
            "tool_data": {
                "auth_policy": auth_result,
            },
            "answer": auth_result.get("reason", "This action is blocked by policy."),
            "auth_result": auth_result,
            "executor_action": action,
        }

    fallback = handle_agent_question(question)
    if isinstance(fallback, dict):
        fallback.setdefault("mode", "fallback_agent")
        return fallback

    return {
        "status": "ok",
        "mode": "fallback_agent",
        "intents": [],
        "used_tools": [],
        "tool_data": {},
        "answer": str(fallback),
    }






ROOM_ACTIVITY_DB_PATH = os.environ.get(
    "HOUSE_ROOM_ACTIVITY_DB_PATH",
    "/home/jnoppe/house-agent/data/room_activity_state.db",
)

_ROOM_ACTIVITY_DB_LOCK = threading.Lock()


def _safe_bool(value):
    """Normalize mixed truthy/falsy sensor values into a strict boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        return v in {"1", "true", "yes", "on", "open", "active", "occupied", "detected"}
    return bool(value)


def _coerce_float(value, default=0.0):
    """Safely convert mixed sensor values to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _utc_now_iso():
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _parse_any_timestamp(value):
    """
    Parse several timestamp formats into a timezone-aware datetime.
    Supports:
    - datetime
    - epoch seconds
    - ISO strings
    - strings ending with Z
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        try:
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except Exception:
            return None

    return None


def _seconds_since_timestamp(value, now_ts=None):
    """Return age in seconds since timestamp. Unknown timestamps return None."""
    ts = _parse_any_timestamp(value)
    if ts is None:
        return None

    now_dt = _parse_any_timestamp(now_ts) if now_ts is not None else datetime.now(timezone.utc)
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    delta = (now_dt - ts).total_seconds()
    if delta < 0:
        return 0.0
    return float(delta)


def _get_room_activity_db_connection():
    """Open SQLite connection for room activity state."""
    db_dir = os.path.dirname(ROOM_ACTIVITY_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(ROOM_ACTIVITY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_room_activity_db():
    """Create SQLite schema for room activity state if needed."""
    with _ROOM_ACTIVITY_DB_LOCK:
        conn = _get_room_activity_db_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS room_activity_state (
                    room_key TEXT PRIMARY KEY,
                    room_name TEXT,
                    room_role TEXT,
                    last_presence_at TEXT,
                    last_motion_at TEXT,
                    last_light_at TEXT,
                    last_access_at TEXT,
                    last_climate_at TEXT,
                    last_evaluated_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_room_activity_updated_at
                ON room_activity_state(updated_at)
                """
            )
            conn.commit()
        finally:
            conn.close()


def _normalize_room_key(room_name):
    """Normalize room key for stable DB storage."""
    return (room_name or "").strip().lower().replace(" ", "_")


def _normalize_room_role(room_name, room_payload):
    """
    Infer room role from room metadata and room name.
    This lets us treat hallway/bathroom/storage differently from desk/living/bedroom.
    """
    payload = room_payload or {}
    name = (room_name or "").strip().lower()

    explicit_role = (
        payload.get("room_role")
        or payload.get("role")
        or payload.get("room_type")
        or payload.get("type")
    )
    if isinstance(explicit_role, str) and explicit_role.strip():
        role = explicit_role.strip().lower()
    else:
        role = ""

    text = f"{name} {role}".strip()

    if any(token in text for token in ["hall", "hallway", "gang", "corridor", "entrance", "entry", "landing", "stairs", "stair"]):
        return "transitional"

    if any(token in text for token in ["bath", "badkamer", "toilet", "wc", "shower"]):
        return "bathroom"

    if any(token in text for token in ["living", "woon", "salon", "tv room", "family room"]):
        return "living"

    if any(token in text for token in ["desk", "office", "bureau", "study", "computer"]):
        return "desk"

    if any(token in text for token in ["bed", "bedroom", "master", "guest room", "slaap"]):
        return "bedroom"

    if any(token in text for token in ["kitchen", "keuken", "dining", "eet"]):
        return "kitchen"

    if any(token in text for token in ["child", "kids", "kid", "nursery", "playroom"]):
        return "child"

    if any(token in text for token in ["attic", "zolder", "loft"]):
        return "attic"

    if any(token in text for token in ["storage", "closet", "utility", "iot", "server", "technical", "tech", "boiler", "meter", "garage", "shed"]):
        return "utility"

    return "general"


def _get_room_role_profile(room_name, room_payload):
    """
    Per-role decay and weighting profile.

    Meaning:
    - presence should dominate strongly everywhere
    - motion should decay quickly in transitional rooms
    - lights mean less in automation-heavy spaces
    - access/NFC should never be treated as strong proof of occupancy on its own
    """
    role = _normalize_room_role(room_name, room_payload)

    profiles = {
        "transitional": {
            "presence_weight": 1.00,
            "motion_weight": 0.80,
            "light_weight": 0.35,
            "access_weight": 0.35,
            "climate_weight": 0.10,
            "presence_recent_seconds": 240,
            "presence_stale_seconds": 900,
            "motion_recent_seconds": 120,
            "motion_stale_seconds": 480,
            "light_recent_seconds": 240,
            "light_stale_seconds": 900,
            "access_recent_seconds": 120,
            "access_stale_seconds": 480,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1200,
            "human_bias": -8,
            "noise_bias": 12,
        },
        "bathroom": {
            "presence_weight": 1.00,
            "motion_weight": 0.85,
            "light_weight": 0.45,
            "access_weight": 0.30,
            "climate_weight": 0.10,
            "presence_recent_seconds": 360,
            "presence_stale_seconds": 1200,
            "motion_recent_seconds": 180,
            "motion_stale_seconds": 720,
            "light_recent_seconds": 300,
            "light_stale_seconds": 1200,
            "access_recent_seconds": 120,
            "access_stale_seconds": 600,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1200,
            "human_bias": -2,
            "noise_bias": 8,
        },
        "living": {
            "presence_weight": 1.10,
            "motion_weight": 0.95,
            "light_weight": 0.55,
            "access_weight": 0.25,
            "climate_weight": 0.10,
            "presence_recent_seconds": 1800,
            "presence_stale_seconds": 5400,
            "motion_recent_seconds": 600,
            "motion_stale_seconds": 2400,
            "light_recent_seconds": 900,
            "light_stale_seconds": 3600,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 10,
            "noise_bias": -6,
        },
        "desk": {
            "presence_weight": 1.15,
            "motion_weight": 0.95,
            "light_weight": 0.55,
            "access_weight": 0.20,
            "climate_weight": 0.10,
            "presence_recent_seconds": 2400,
            "presence_stale_seconds": 7200,
            "motion_recent_seconds": 900,
            "motion_stale_seconds": 3600,
            "light_recent_seconds": 1200,
            "light_stale_seconds": 4800,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 12,
            "noise_bias": -8,
        },
        "bedroom": {
            "presence_weight": 1.10,
            "motion_weight": 0.90,
            "light_weight": 0.40,
            "access_weight": 0.20,
            "climate_weight": 0.10,
            "presence_recent_seconds": 2400,
            "presence_stale_seconds": 7200,
            "motion_recent_seconds": 900,
            "motion_stale_seconds": 3600,
            "light_recent_seconds": 900,
            "light_stale_seconds": 3600,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 8,
            "noise_bias": -4,
        },
        "kitchen": {
            "presence_weight": 1.05,
            "motion_weight": 0.95,
            "light_weight": 0.50,
            "access_weight": 0.25,
            "climate_weight": 0.10,
            "presence_recent_seconds": 1200,
            "presence_stale_seconds": 3600,
            "motion_recent_seconds": 420,
            "motion_stale_seconds": 1800,
            "light_recent_seconds": 600,
            "light_stale_seconds": 2400,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 8,
            "noise_bias": -3,
        },
        "child": {
            "presence_weight": 1.05,
            "motion_weight": 0.95,
            "light_weight": 0.45,
            "access_weight": 0.20,
            "climate_weight": 0.10,
            "presence_recent_seconds": 1800,
            "presence_stale_seconds": 5400,
            "motion_recent_seconds": 600,
            "motion_stale_seconds": 2400,
            "light_recent_seconds": 900,
            "light_stale_seconds": 3600,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 8,
            "noise_bias": -3,
        },
        "attic": {
            "presence_weight": 1.00,
            "motion_weight": 0.90,
            "light_weight": 0.40,
            "access_weight": 0.25,
            "climate_weight": 0.10,
            "presence_recent_seconds": 900,
            "presence_stale_seconds": 3000,
            "motion_recent_seconds": 360,
            "motion_stale_seconds": 1500,
            "light_recent_seconds": 600,
            "light_stale_seconds": 2400,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 0,
            "noise_bias": 2,
        },
        "utility": {
            "presence_weight": 0.95,
            "motion_weight": 0.70,
            "light_weight": 0.25,
            "access_weight": 0.25,
            "climate_weight": 0.15,
            "presence_recent_seconds": 420,
            "presence_stale_seconds": 1500,
            "motion_recent_seconds": 120,
            "motion_stale_seconds": 600,
            "light_recent_seconds": 240,
            "light_stale_seconds": 1200,
            "access_recent_seconds": 120,
            "access_stale_seconds": 600,
            "climate_recent_seconds": 420,
            "climate_stale_seconds": 1800,
            "human_bias": -12,
            "noise_bias": 18,
        },
        "general": {
            "presence_weight": 1.00,
            "motion_weight": 0.90,
            "light_weight": 0.45,
            "access_weight": 0.25,
            "climate_weight": 0.10,
            "presence_recent_seconds": 1200,
            "presence_stale_seconds": 3600,
            "motion_recent_seconds": 420,
            "motion_stale_seconds": 1800,
            "light_recent_seconds": 600,
            "light_stale_seconds": 2400,
            "access_recent_seconds": 180,
            "access_stale_seconds": 900,
            "climate_recent_seconds": 300,
            "climate_stale_seconds": 1800,
            "human_bias": 0,
            "noise_bias": 0,
        },
    }

    profile = profiles.get(role, profiles["general"]).copy()
    profile["role"] = role
    return profile


def _get_decay_factor_from_age(age_seconds, recent_seconds, stale_seconds):
    """Convert age into a smooth decay factor."""
    if age_seconds is None:
        return 0.85, "unknown"

    if age_seconds <= recent_seconds:
        return 1.00, "fresh"

    if age_seconds >= stale_seconds:
        return 0.35, "stale"

    span = max(stale_seconds - recent_seconds, 1)
    progress = (age_seconds - recent_seconds) / span
    decay = 1.00 - (0.65 * progress)
    return round(max(0.35, min(1.00, decay)), 3), "aging"


def _load_room_activity_state(room_name):
    """Load stored room activity state from SQLite."""
    _ensure_room_activity_db()
    room_key = _normalize_room_key(room_name)

    with _ROOM_ACTIVITY_DB_LOCK:
        conn = _get_room_activity_db_connection()
        try:
            row = conn.execute(
                """
                SELECT *
                FROM room_activity_state
                WHERE room_key = ?
                """,
                (room_key,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def _upsert_room_activity_state(room_name, room_payload, now_iso=None):
    """
    Persist latest room signal activity to SQLite.
    Uses normalized room snapshot extracted from the real /ai/house_sensors payload.
    """
    _ensure_room_activity_db()

    normalized = _extract_room_signal_snapshot(room_name, room_payload)
    room_key = _normalize_room_key(room_name)
    room_role = _normalize_room_role(room_name, normalized)
    now_iso = now_iso or _utc_now_iso()

    presence = _safe_bool(normalized.get("presence"))
    motion = _safe_bool(normalized.get("motion"))
    lights_on = _safe_bool(normalized.get("lights_on"))
    access_active = _safe_bool(normalized.get("access_active"))
    climate_active = _safe_bool(normalized.get("climate_active"))

    with _ROOM_ACTIVITY_DB_LOCK:
        conn = _get_room_activity_db_connection()
        try:
            row = conn.execute(
                """
                SELECT *
                FROM room_activity_state
                WHERE room_key = ?
                """,
                (room_key,),
            ).fetchone()

            existing = dict(row) if row else {}

            last_presence_at = (
                normalized.get("last_presence_at") or now_iso
                if presence else existing.get("last_presence_at")
            )
            last_motion_at = (
                normalized.get("last_motion_at") or now_iso
                if motion else existing.get("last_motion_at")
            )
            last_light_at = (
                normalized.get("last_light_at") or now_iso
                if lights_on else existing.get("last_light_at")
            )
            last_access_at = (
                normalized.get("last_access_at") or now_iso
                if access_active else existing.get("last_access_at")
            )
            last_climate_at = (
                normalized.get("last_climate_at") or now_iso
                if climate_active else existing.get("last_climate_at")
            )
            created_at = existing.get("created_at") or now_iso

            conn.execute("BEGIN IMMEDIATE")

            conn.execute(
                """
                INSERT INTO room_activity_state (
                    room_key,
                    room_name,
                    room_role,
                    last_presence_at,
                    last_motion_at,
                    last_light_at,
                    last_access_at,
                    last_climate_at,
                    last_evaluated_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(room_key) DO UPDATE SET
                    room_name = excluded.room_name,
                    room_role = excluded.room_role,
                    last_presence_at = excluded.last_presence_at,
                    last_motion_at = excluded.last_motion_at,
                    last_light_at = excluded.last_light_at,
                    last_access_at = excluded.last_access_at,
                    last_climate_at = excluded.last_climate_at,
                    last_evaluated_at = excluded.last_evaluated_at,
                    updated_at = excluded.updated_at
                """,
                (
                    room_key,
                    normalized.get("room") or room_name,
                    room_role,
                    last_presence_at,
                    last_motion_at,
                    last_light_at,
                    last_access_at,
                    last_climate_at,
                    now_iso,
                    created_at,
                    now_iso,
                ),
            )

            conn.execute("COMMIT")

            return {
                "room_key": room_key,
                "room_name": normalized.get("room") or room_name,
                "room_role": room_role,
                "last_presence_at": last_presence_at,
                "last_motion_at": last_motion_at,
                "last_light_at": last_light_at,
                "last_access_at": last_access_at,
                "last_climate_at": last_climate_at,
                "last_evaluated_at": now_iso,
                "created_at": created_at,
                "updated_at": now_iso,
            }
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()



def _build_room_recency_snapshot(room_name, room_payload, now_ts=None):
    """
    Build recency snapshot from SQLite-backed room memory.
    This is the core of persistent room awareness.
    """
    payload = room_payload or {}
    profile = _get_room_role_profile(room_name, payload)
    state = _load_room_activity_state(room_name) or {}

    presence_age = _seconds_since_timestamp(state.get("last_presence_at"), now_ts=now_ts)
    motion_age = _seconds_since_timestamp(state.get("last_motion_at"), now_ts=now_ts)
    light_age = _seconds_since_timestamp(state.get("last_light_at"), now_ts=now_ts)
    access_age = _seconds_since_timestamp(state.get("last_access_at"), now_ts=now_ts)
    climate_age = _seconds_since_timestamp(state.get("last_climate_at"), now_ts=now_ts)

    presence_decay, presence_band = _get_decay_factor_from_age(
        presence_age,
        profile["presence_recent_seconds"],
        profile["presence_stale_seconds"],
    )
    motion_decay, motion_band = _get_decay_factor_from_age(
        motion_age,
        profile["motion_recent_seconds"],
        profile["motion_stale_seconds"],
    )
    light_decay, light_band = _get_decay_factor_from_age(
        light_age,
        profile["light_recent_seconds"],
        profile["light_stale_seconds"],
    )
    access_decay, access_band = _get_decay_factor_from_age(
        access_age,
        profile["access_recent_seconds"],
        profile["access_stale_seconds"],
    )
    climate_decay, climate_band = _get_decay_factor_from_age(
        climate_age,
        profile["climate_recent_seconds"],
        profile["climate_stale_seconds"],
    )

    known_ages = [v for v in [presence_age, motion_age, light_age, access_age, climate_age] if v is not None]
    latest_activity_age = min(known_ages) if known_ages else None

    if presence_band == "fresh":
        dominant_band = "fresh"
    elif motion_band == "fresh":
        dominant_band = "fresh"
    elif latest_activity_age is None:
        dominant_band = "unknown"
    elif latest_activity_age > max(
        profile["presence_stale_seconds"],
        profile["motion_stale_seconds"],
        profile["light_stale_seconds"],
        profile["access_stale_seconds"],
        profile["climate_stale_seconds"],
    ):
        dominant_band = "stale"
    else:
        dominant_band = "aging"

    return {
        "room_role": profile["role"],
        "presence_age_seconds": presence_age,
        "motion_age_seconds": motion_age,
        "light_age_seconds": light_age,
        "access_age_seconds": access_age,
        "climate_age_seconds": climate_age,
        "presence_decay_factor": presence_decay,
        "motion_decay_factor": motion_decay,
        "light_decay_factor": light_decay,
        "access_decay_factor": access_decay,
        "climate_decay_factor": climate_decay,
        "presence_recency_band": presence_band,
        "motion_recency_band": motion_band,
        "light_recency_band": light_band,
        "access_recency_band": access_band,
        "climate_recency_band": climate_band,
        "latest_activity_age_seconds": latest_activity_age,
        "recency_band": dominant_band,
        "state": state,
    }


def _analyze_room_activity_reason(room_name, room_payload, now_ts=None):
    """
    Human-readable explanation of why a room looks active.

    This version is:
    - role-aware
    - SQLite-backed
    - recency-aware per signal type
    """
    payload = room_payload or {}
    profile = _get_room_role_profile(room_name, payload)
    recency = _build_room_recency_snapshot(room_name, payload, now_ts=now_ts)

    presence = _safe_bool(payload.get("presence"))
    motion = _safe_bool(payload.get("motion"))
    lights_on = _safe_bool(payload.get("lights_on") or payload.get("light_on") or payload.get("lighting_active"))
    access_active = _safe_bool(payload.get("door_open") or payload.get("door_active") or payload.get("nfc_active") or payload.get("access_active"))
    climate_active = _safe_bool(payload.get("climate_active") or payload.get("heating_active") or payload.get("hvac_active") or payload.get("temperature_control_active"))

    reasons = []
    primary = "unknown"
    secondary = None
    confidence = "low"

    if presence:
        primary = "presence_detected"
        confidence = "high"
        reasons.append("presence is currently detected")

        if motion:
            secondary = "motion_detected"
            reasons.append("motion is also active")

        if lights_on:
            reasons.append("lights are on")

    elif motion:
        if recency["motion_recency_band"] == "fresh":
            primary = "recent_motion"
            confidence = "medium"
            reasons.append("recent motion suggests recent human activity")
        else:
            primary = "stale_motion"
            confidence = "low"
            reasons.append("motion was seen earlier, but it is no longer very recent")

        if lights_on:
            secondary = "lights_on"
            reasons.append("lights remain on")

    elif access_active:
        primary = "access_triggered"
        confidence = "low"
        reasons.append("there was an access-related trigger")
        reasons.append("access alone is not strong proof of ongoing presence")

        if lights_on:
            secondary = "lights_on"
            reasons.append("lights remain on after access activity")

    elif lights_on:
        primary = "lights_only"
        confidence = "low"
        reasons.append("lights are on without stronger live human signals")

    elif climate_active:
        primary = "background_automation"
        confidence = "low"
        reasons.append("climate or automation activity is present")
        reasons.append("this looks more like background system behavior")

    else:
        # fallback to stored memory
        if recency["presence_recency_band"] == "fresh":
            primary = "recent_presence_memory"
            confidence = "medium"
            reasons.append("this room had recent strong presence memory")
        elif recency["motion_recency_band"] in {"fresh", "aging"}:
            primary = "recent_motion_memory"
            confidence = "low"
            reasons.append("this room had recent motion memory")
        else:
            primary = "idle"
            confidence = "low"
            reasons.append("no strong activity signals are currently active")

    if profile["role"] in {"transitional", "bathroom", "utility"} and primary in {
        "recent_motion",
        "stale_motion",
        "lights_only",
        "access_triggered",
        "recent_motion_memory",
    }:
        reasons.append(f"{profile['role']} rooms should decay faster than true occupied rooms")

    return {
        "activity_reason": "; ".join(reasons),
        "activity_reason_primary": primary,
        "activity_reason_secondary": secondary,
        "activity_reason_confidence": confidence,
    }



def _clamp01(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def _classification_priority_weight(classification: str) -> float:
    mapping = {
        "occupied": 1.00,
        "transient": 0.68,
        "passive": 0.42,
        "uncertain": 0.30,
        "idle": 0.05,
    }
    return mapping.get(str(classification or "").strip().lower(), 0.05)


def _classify_room_state(
    *,
    room_role: str,
    presence: bool,
    motion: bool,
    lights_on: bool,
    access_active: bool,
    climate_active: bool,
    recency: dict,
    human_activity_score: int,
):
    """
    Explicit Room Reasoning V2 classification layer.

    Returns one of:
    - occupied
    - transient
    - passive
    - idle
    - uncertain
    """
    role = str(room_role or "general").lower()
    presence_band = str(recency.get("presence_recency_band") or "unknown").lower()
    motion_band = str(recency.get("motion_recency_band") or "unknown").lower()
    recency_band = str(recency.get("recency_band") or "unknown").lower()

    transitional_roles = {"transitional", "bathroom"}
    sustained_roles = {"living", "desk", "bedroom", "kitchen", "child"}

    if presence:
        return "occupied"

    if motion and not presence:
        if role in transitional_roles:
            return "transient"
        if role in sustained_roles and motion_band == "fresh" and human_activity_score >= 45:
            return "uncertain"
        return "transient" if motion_band == "fresh" else "uncertain"

    if not presence and not motion:
        if lights_on or climate_active or access_active:
            if role == "utility":
                return "passive"
            if lights_on and not access_active and not climate_active:
                return "passive"
            if climate_active and not lights_on:
                return "passive"
            if access_active and role in transitional_roles:
                return "transient"
            return "passive"

    if not presence and not motion:
        if presence_band == "fresh" and human_activity_score >= 45:
            return "uncertain"
        if recency_band in {"aging"} and human_activity_score >= 35:
            return "uncertain"
        return "idle"

    return "uncertain"


def _compute_confidence_score(
    *,
    classification: str,
    room_role: str,
    presence: bool,
    motion: bool,
    lights_on: bool,
    access_active: bool,
    climate_active: bool,
    recency: dict,
    human_activity_score: int,
):
    role = str(room_role or "general").lower()
    motion_band = str(recency.get("motion_recency_band") or "unknown").lower()
    presence_band = str(recency.get("presence_recency_band") or "unknown").lower()
    recency_band = str(recency.get("recency_band") or "unknown").lower()

    score = 0.45

    if classification == "occupied":
        score = 0.72
        if presence:
            score += 0.12
        if motion:
            score += 0.08
        if lights_on:
            score += 0.05
        if access_active:
            score += 0.03
        if role in {"living", "desk", "bedroom", "kitchen", "child"}:
            score += 0.03

    elif classification == "transient":
        score = 0.58
        if motion:
            score += 0.10
        if access_active:
            score += 0.06
        if role in {"transitional", "bathroom"}:
            score += 0.06
        if lights_on:
            score -= 0.03
        if climate_active:
            score -= 0.04

    elif classification == "passive":
        score = 0.60
        if lights_on:
            score += 0.06
        if climate_active:
            score += 0.05
        if not motion and not presence:
            score += 0.05
        if role == "utility":
            score += 0.05

    elif classification == "idle":
        score = 0.82
        if recency_band == "stale":
            score += 0.06
        if presence_band == "fresh" or motion_band == "fresh":
            score -= 0.18

    elif classification == "uncertain":
        score = 0.48
        if presence_band == "fresh":
            score += 0.08
        if motion_band == "fresh":
            score += 0.05
        if lights_on:
            score += 0.03
        if climate_active:
            score -= 0.03

    # gently blend in current score signal
    score += (max(0, min(100, int(human_activity_score))) / 100.0 - 0.5) * 0.10

    return round(_clamp01(score), 2)


def _compute_human_likelihood(
    *,
    classification: str,
    room_role: str,
    presence: bool,
    motion: bool,
    lights_on: bool,
    access_active: bool,
    climate_active: bool,
    recency: dict,
    human_activity_score: int,
):
    role = str(room_role or "general").lower()
    motion_band = str(recency.get("motion_recency_band") or "unknown").lower()
    presence_band = str(recency.get("presence_recency_band") or "unknown").lower()

    value = 0.08

    if presence:
        value += 0.62
    if motion:
        value += 0.18
    if motion_band == "fresh":
        value += 0.06
    if presence_band == "fresh":
        value += 0.08
    if lights_on:
        value += 0.04
    if access_active:
        value += 0.03

    if climate_active and not presence and not motion:
        value -= 0.08

    if role in {"living", "desk", "bedroom", "kitchen", "child"}:
        value += 0.05
    if role in {"transitional", "bathroom"} and not presence:
        value -= 0.08
    if role == "utility":
        value -= 0.14

    if classification == "occupied":
        value += 0.10
    elif classification == "transient":
        value += 0.03
    elif classification == "passive":
        value -= 0.10
    elif classification == "idle":
        value -= 0.20
    elif classification == "uncertain":
        value -= 0.03

    value += (max(0, min(100, int(human_activity_score))) / 100.0 - 0.5) * 0.18

    return round(_clamp01(value), 2)


def _compute_automation_likelihood(
    *,
    classification: str,
    room_role: str,
    presence: bool,
    motion: bool,
    lights_on: bool,
    access_active: bool,
    climate_active: bool,
    recency: dict,
    automation_noise_likelihood: str,
):
    role = str(room_role or "general").lower()
    recency_band = str(recency.get("recency_band") or "unknown").lower()

    value = 0.10

    if climate_active:
        value += 0.24
    if lights_on and not presence and not motion:
        value += 0.18
    if access_active and not presence and not motion:
        value += 0.10
    if role == "utility":
        value += 0.22
    if role in {"transitional", "bathroom"} and not presence:
        value += 0.10
    if recency_band == "stale":
        value += 0.10

    if presence:
        value -= 0.28
    if motion and str(recency.get("motion_recency_band") or "").lower() == "fresh":
        value -= 0.10

    if classification == "passive":
        value += 0.12
    elif classification == "idle":
        value += 0.05
    elif classification == "occupied":
        value -= 0.18
    elif classification == "transient":
        value -= 0.04

    noise = str(automation_noise_likelihood or "low").lower()
    if noise == "high":
        value += 0.15
    elif noise == "medium":
        value += 0.06

    return round(_clamp01(value), 2)


def _compute_priority_score(
    *,
    classification: str,
    confidence_score: float,
    human_likelihood: float,
    human_activity_score: int,
    recency: dict,
):
    class_weight = _classification_priority_weight(classification)
    freshness_bonus = 1.0

    if str(recency.get("recency_band") or "").lower() == "fresh":
        freshness_bonus = 1.05
    elif str(recency.get("recency_band") or "").lower() == "stale":
        freshness_bonus = 0.82

    base = class_weight * max(0.35, float(human_likelihood)) * float(confidence_score)
    score_norm = max(0.0, min(1.0, int(human_activity_score) / 100.0))
    final = (base * 0.82) + (score_norm * 0.18)
    final *= freshness_bonus

    return round(_clamp01(final), 2)


def _build_reason_factors(
    *,
    classification: str,
    room_role: str,
    presence: bool,
    motion: bool,
    lights_on: bool,
    access_active: bool,
    climate_active: bool,
    recency: dict,
):
    factors = []
    role = str(room_role or "general").lower()
    presence_band = str(recency.get("presence_recency_band") or "unknown").lower()
    motion_band = str(recency.get("motion_recency_band") or "unknown").lower()
    recency_band = str(recency.get("recency_band") or "unknown").lower()

    if presence:
        factors.append("stable presence is currently detected")

    if motion:
        if motion_band == "fresh":
            factors.append("recent motion supports active use")
        else:
            factors.append("motion is present but not fully fresh")

    if lights_on:
        factors.append("lights are currently on")

    if access_active:
        factors.append("recent access-related activity is visible")

    if climate_active:
        if not presence and not motion:
            factors.append("climate-related activity is present without clear occupancy")
        else:
            factors.append("climate activity is also present")

    if not presence and not motion and not lights_on and not access_active and not climate_active:
        factors.append("no strong live activity signals are currently visible")

    if not presence and presence_band == "fresh":
        factors.append("recent presence memory is still influencing room state")

    if not motion and motion_band in {"fresh", "aging"} and classification in {"transient", "uncertain"}:
        factors.append("recent motion memory is still contributing")

    if role in {"transitional", "bathroom"} and classification in {"transient", "passive", "uncertain"}:
        factors.append("this room type usually reflects passing activity rather than sustained use")

    if role == "utility" and classification in {"passive", "idle", "uncertain"}:
        factors.append("this room is more likely to reflect system or background activity")

    if recency_band == "stale" and classification != "occupied":
        factors.append("the strongest signals are no longer fresh")

    # remove duplicates while preserving order
    deduped = []
    seen = set()
    for item in factors:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:6]


def _build_room_reasoning_summary(
    *,
    room_name: str,
    classification: str,
    confidence_score: float,
    reason_factors: list,
):
    label = _human_room_label(room_name)
    factors = reason_factors or []

    top = factors[:2]
    tail = factors[2:4]

    if classification == "occupied":
        if top:
            return f"{label} appears occupied because {_join_natural(top)}."
        return f"{label} appears occupied."

    if classification == "transient":
        if top:
            return f"{label} shows passing activity because {_join_natural(top)}."
        return f"{label} shows passing activity rather than sustained room use."

    if classification == "passive":
        if top:
            return f"{label} appears active, but the pattern looks more like background automation because {_join_natural(top)}."
        return f"{label} appears active, but more like background automation than human use."

    if classification == "idle":
        if top:
            return f"{label} currently looks idle because {_join_natural(top)}."
        return f"{label} currently looks idle."

    if classification == "uncertain":
        if top and tail:
            return f"{label} shows mixed signals: {_join_natural(top)}, with {_join_natural(tail)} also contributing."
        if top:
            return f"{label} shows mixed signals because {_join_natural(top)}."
        return f"{label} shows mixed signals and cannot yet be classified confidently."

    return f"{label} could not be classified clearly."


def _score_room_intelligence(room_name, room_payload, now_ts=None):
    """
    Room Reasoning V2

    Keeps the existing score/decay architecture, but adds:
    - explicit classification
    - confidence_score (0..1)
    - human_likelihood (0..1)
    - automation_likelihood (0..1)
    - priority_score (0..1)
    - reason_factors
    - natural summary
    """
    payload = room_payload or {}
    profile = _get_room_role_profile(room_name, payload)
    recency = _build_room_recency_snapshot(room_name, payload, now_ts=now_ts)
    reason_info = _analyze_room_activity_reason(room_name, payload, now_ts=now_ts)

    presence = _safe_bool(payload.get("presence"))
    motion = _safe_bool(payload.get("motion"))
    lights_on = _safe_bool(payload.get("lights_on") or payload.get("light_on") or payload.get("lighting_active"))
    access_active = _safe_bool(
        payload.get("door_open")
        or payload.get("door_active")
        or payload.get("nfc_active")
        or payload.get("access_active")
    )
    climate_active = _safe_bool(
        payload.get("climate_active")
        or payload.get("heating_active")
        or payload.get("hvac_active")
        or payload.get("temperature_control_active")
    )

    # existing score logic retained and lightly cleaned
    base_score = 0.0

    if presence:
        base_score += 65.0 * profile["presence_weight"]
    else:
        if recency["presence_decay_factor"] > 0.60 and recency["presence_age_seconds"] is not None:
            base_score += 18.0 * profile["presence_weight"] * recency["presence_decay_factor"]

    if motion:
        base_score += 24.0 * profile["motion_weight"]
    else:
        if recency["motion_age_seconds"] is not None:
            base_score += 14.0 * profile["motion_weight"] * recency["motion_decay_factor"]

    if lights_on:
        base_score += 10.0 * profile["light_weight"]
    else:
        if recency["light_age_seconds"] is not None and recency["light_decay_factor"] > 0.55:
            base_score += 4.0 * profile["light_weight"] * recency["light_decay_factor"]

    if access_active:
        base_score += 8.0 * profile["access_weight"]
    else:
        if recency["access_age_seconds"] is not None and recency["access_decay_factor"] > 0.60:
            base_score += 3.0 * profile["access_weight"] * recency["access_decay_factor"]

    if climate_active:
        base_score += 4.0 * profile["climate_weight"]
    else:
        if recency["climate_age_seconds"] is not None and recency["climate_decay_factor"] > 0.65:
            base_score += 2.0 * profile["climate_weight"] * recency["climate_decay_factor"]

    base_score += profile["human_bias"]

    if access_active and not presence and not motion:
        base_score -= 8.0

    if climate_active and not presence and not motion and not lights_on:
        base_score -= 10.0

    if lights_on and not presence and not motion and not access_active:
        base_score -= 6.0

    if recency["recency_band"] == "stale" and not presence:
        base_score *= 0.75

    human_activity_score = int(round(max(0.0, min(100.0, base_score))))

    if presence and human_activity_score >= 65:
        occupancy_confidence = "high"
    elif human_activity_score >= 35:
        occupancy_confidence = "medium"
    else:
        occupancy_confidence = "low"

    noise_score = 0

    if climate_active:
        noise_score += 28
    elif recency["climate_decay_factor"] > 0.60 and recency["climate_age_seconds"] is not None:
        noise_score += 16

    if lights_on and not presence and not motion:
        noise_score += 18
    if access_active and not presence and not motion:
        noise_score += 14
    if profile["role"] in {"utility", "transitional"}:
        noise_score += 18
    if recency["recency_band"] == "stale":
        noise_score += 16
    if presence:
        noise_score -= 40
    if motion and recency["motion_recency_band"] == "fresh":
        noise_score -= 20

    noise_score += profile["noise_bias"]
    noise_score = max(0, min(100, noise_score))

    if noise_score >= 55:
        automation_noise_likelihood = "high"
    elif noise_score >= 28:
        automation_noise_likelihood = "medium"
    else:
        automation_noise_likelihood = "low"

    classification = _classify_room_state(
        room_role=profile["role"],
        presence=presence,
        motion=motion,
        lights_on=lights_on,
        access_active=access_active,
        climate_active=climate_active,
        recency=recency,
        human_activity_score=human_activity_score,
    )

    confidence_score = _compute_confidence_score(
        classification=classification,
        room_role=profile["role"],
        presence=presence,
        motion=motion,
        lights_on=lights_on,
        access_active=access_active,
        climate_active=climate_active,
        recency=recency,
        human_activity_score=human_activity_score,
    )

    human_likelihood = _compute_human_likelihood(
        classification=classification,
        room_role=profile["role"],
        presence=presence,
        motion=motion,
        lights_on=lights_on,
        access_active=access_active,
        climate_active=climate_active,
        recency=recency,
        human_activity_score=human_activity_score,
    )

    automation_likelihood = _compute_automation_likelihood(
        classification=classification,
        room_role=profile["role"],
        presence=presence,
        motion=motion,
        lights_on=lights_on,
        access_active=access_active,
        climate_active=climate_active,
        recency=recency,
        automation_noise_likelihood=automation_noise_likelihood,
    )

    priority_score = _compute_priority_score(
        classification=classification,
        confidence_score=confidence_score,
        human_likelihood=human_likelihood,
        human_activity_score=human_activity_score,
        recency=recency,
    )

    reason_factors = _build_reason_factors(
        classification=classification,
        room_role=profile["role"],
        presence=presence,
        motion=motion,
        lights_on=lights_on,
        access_active=access_active,
        climate_active=climate_active,
        recency=recency,
    )

    summary = _build_room_reasoning_summary(
        room_name=room_name,
        classification=classification,
        confidence_score=confidence_score,
        reason_factors=reason_factors,
    )

    result = {
        "room_role": profile["role"],
        "recency_band": recency["recency_band"],
        "latest_activity_age_seconds": recency["latest_activity_age_seconds"],
        "presence_age_seconds": recency["presence_age_seconds"],
        "motion_age_seconds": recency["motion_age_seconds"],
        "light_age_seconds": recency["light_age_seconds"],
        "access_age_seconds": recency["access_age_seconds"],
        "climate_age_seconds": recency["climate_age_seconds"],
        "presence_decay_factor": recency["presence_decay_factor"],
        "motion_decay_factor": recency["motion_decay_factor"],
        "light_decay_factor": recency["light_decay_factor"],
        "access_decay_factor": recency["access_decay_factor"],
        "climate_decay_factor": recency["climate_decay_factor"],
        "human_activity_score": human_activity_score,
        "occupancy_confidence": occupancy_confidence,
        "automation_noise_likelihood": automation_noise_likelihood,

        # V2 fields
        "classification": classification,
        "confidence_score": confidence_score,
        "human_likelihood": human_likelihood,
        "automation_likelihood": automation_likelihood,
        "priority_score": priority_score,
        "reason_factors": reason_factors,
        "summary": summary,
    }

    result.update(reason_info)
    return result





def _build_ranked_room_intelligence(sensor_payload):
    """
    Build ranked list of room intelligence records from enriched /ai/house_sensors payload.
    V2 ranking prefers explicit room priority first.
    """
    if not isinstance(sensor_payload, dict):
        return []

    rooms = sensor_payload.get("rooms")
    if not isinstance(rooms, list):
        return []

    ranked = []

    for room_payload in rooms:
        item = dict(room_payload or {})
        item["room_name"] = item.get("room") or "unknown_room"
        ranked.append(item)

    ranked.sort(
        key=lambda r: (
            float(r.get("priority_score", 0.0) or 0.0),
            int(r.get("human_activity_score", 0) or 0),
            float(r.get("confidence_score", 0.0) or 0.0),
            1 if str(r.get("classification", "")).lower() == "occupied" else 0,
        ),
        reverse=True,
    )

    return ranked


def _summarize_house_sensors(sensor_result, action=None, question=None, user_question=None):
    """
    V2 house sensor summary:
    - uses explicit classification
    - uses room summaries
    - better room-specific responses
    """
    if not isinstance(sensor_result, dict):
        return "I could not read the house sensor data."

    payload = sensor_result
    if isinstance(sensor_result.get("data"), dict):
        payload = sensor_result.get("data") or {}

    if not isinstance(payload, dict):
        return "I could not read the house sensor payload."

    enriched_payload = _enrich_house_sensor_payload_with_activity_reasons(payload)
    ranked_rooms = _build_ranked_room_intelligence(enriched_payload)

    if not ranked_rooms:
        return "I could not determine room activity right now."

    actual_question = question if question is not None else user_question
    actual_question = (actual_question or "").strip().lower()

    human_rooms = _filter_human_likely_rooms(ranked_rooms)
    background_rooms = _filter_background_like_rooms(ranked_rooms)
    most_active_room = ranked_rooms[0] if ranked_rooms else None

    if any(
        phrase in actual_question
        for phrase in [
            "most active room",
            "which room is most active",
            "what room is most active",
            "most active",
        ]
    ):
        if most_active_room:
            room_name = most_active_room.get("room_name") or most_active_room.get("room") or "unknown room"
            classification = most_active_room.get("classification") or "unknown"
            confidence_score = most_active_room.get("confidence_score", 0.0)
            score = most_active_room.get("human_activity_score", 0)
            summary = most_active_room.get("summary")

            if summary:
                return (
                    f"The most important active room right now is {room_name}. "
                    f"It is classified as {classification} with confidence {round(float(confidence_score) * 100)} percent. "
                    f"{summary}"
                )

            return (
                f"The most important active room right now is {room_name}. "
                f"It is classified as {classification} with a human activity score of {score}/100."
            )
        return "I could not determine the most active room right now."

    if any(
        phrase in actual_question
        for phrase in [
            "recently used by a person",
            "recently used",
            "likely being used",
            "used by a person",
            "human activity",
            "which rooms are likely being used",
            "what rooms are likely being used",
            "which rooms are probably being used",
            "what rooms are probably being used",
        ]
    ):
        if human_rooms:
            lines = []
            for room in human_rooms[:5]:
                room_name = room.get("room_name") or room.get("room") or "unknown room"
                classification = room.get("classification") or "unknown"
                confidence_score = round(float(room.get("confidence_score", 0.0) or 0.0) * 100)
                lines.append(f"{room_name} ({classification}, {confidence_score} percent confidence)")
            return "The rooms most likely showing real human use right now are: " + ", ".join(lines) + "."
        return "I do not currently see strong signs of real human room use."

    if any(
        phrase in actual_question
        for phrase in [
            "background automation",
            "just background",
            "automation only",
            "probably just automation",
            "which rooms look like automation",
            "what rooms look like automation",
        ]
    ):
        if background_rooms:
            lines = []
            for room in background_rooms[:5]:
                room_name = room.get("room_name") or room.get("room") or "unknown room"
                classification = room.get("classification") or "unknown"
                automation_likelihood = round(float(room.get("automation_likelihood", 0.0) or 0.0) * 100)
                lines.append(f"{room_name} ({classification}, automation likelihood {automation_likelihood} percent)")
            return "The rooms that currently look most like background automation are: " + ", ".join(lines) + "."
        return "I do not currently see rooms that strongly look like background automation."

    def _normalize_question_room_guess(text: str) -> str:
        guess = (text or "").strip().lower()
        guess = guess.replace("?", "").strip()

        prefixes = [
            "why is ",
            "what is happening in ",
            "what's happening in ",
            "what is active in ",
            "what sensors are active in ",
            "give me the current state of ",
            "current state of ",
            "is anyone in ",
            "is anyone in the ",
            "is the ",
        ]
        for prefix in prefixes:
            if guess.startswith(prefix):
                guess = guess[len(prefix):].strip()
                break

        if guess.startswith("the "):
            guess = guess[4:].strip()

        suffixes = [
            " active",
            " right now",
            " currently",
            " occupied",
            " in use",
        ]
        changed = True
        while changed:
            changed = False
            for suffix in suffixes:
                if guess.endswith(suffix):
                    guess = guess[: -len(suffix)].strip()
                    changed = True

        return guess.replace(" ", "")

    normalized_room_guess = None

    if any(
        actual_question.startswith(prefix)
        for prefix in [
            "why is ",
            "what is happening in ",
            "what's happening in ",
            "what is active in ",
            "what sensors are active in ",
            "give me the current state of ",
            "current state of ",
            "is anyone in ",
            "is anyone in the ",
        ]
    ):
        normalized_room_guess = _normalize_question_room_guess(actual_question)

    if normalized_room_guess:
        for room in ranked_rooms:
            room_name_raw = (room.get("room_name") or room.get("room") or "").strip()
            room_name_normalized = room_name_raw.lower().replace(" ", "")

            if room_name_normalized == normalized_room_guess:
                classification = room.get("classification") or "unknown"
                summary = room.get("summary") or "I could not determine a clear room summary."
                confidence_score = round(float(room.get("confidence_score", 0.0) or 0.0) * 100)
                human_likelihood = round(float(room.get("human_likelihood", 0.0) or 0.0) * 100)
                automation_likelihood = round(float(room.get("automation_likelihood", 0.0) or 0.0) * 100)
                reason_factors = room.get("reason_factors") or []

                detail_bits = []
                if reason_factors:
                    detail_bits.append("Key factors: " + "; ".join(reason_factors[:4]) + ".")
                detail_bits.append(
                    f"It is classified as {classification} with confidence {confidence_score} percent."
                )
                detail_bits.append(
                    f"Human likelihood is {human_likelihood} percent and automation likelihood is {automation_likelihood} percent."
                )

                return summary + " " + " ".join(detail_bits)

    if any(
        phrase in actual_question
        for phrase in [
            "which rooms are occupied",
            "what rooms are occupied",
            "occupancy",
            "is anyone home",
            "is anyone downstairs",
        ]
    ):
        occupied_rooms = [r for r in ranked_rooms if str(r.get("classification", "")).lower() == "occupied"]
        if occupied_rooms:
            names = [r.get("room_name") or r.get("room") or "unknown room" for r in occupied_rooms[:6]]
            return "The rooms that currently look occupied are: " + ", ".join(names) + "."
        return "I do not currently see any rooms that confidently look occupied."

    human_names = [room.get("room_name") or room.get("room") or "unknown room" for room in human_rooms[:5]]
    background_names = [room.get("room_name") or room.get("room") or "unknown room" for room in background_rooms[:5]]

    summary_parts = []

    if most_active_room:
        summary_parts.append(
            most_active_room.get("summary")
            or f"The most important active room appears to be {most_active_room.get('room_name') or most_active_room.get('room')}."
        )

    if human_names:
        summary_parts.append("Rooms most likely showing human use: " + ", ".join(human_names) + ".")

    if background_names:
        summary_parts.append("Rooms that look more like background automation: " + ", ".join(background_names) + ".")

    if not summary_parts:
        return "I could not build a useful house sensor summary right now."

    return " ".join(summary_parts)






def _filter_human_likely_rooms(ranked_rooms):
    """
    Keep rooms that most likely represent real human use.
    Designed to be stricter for hallway/bathroom/utility rooms.
    """
    results = []

    for room in ranked_rooms or []:
        score = int(room.get("human_activity_score", 0))
        occupancy_confidence = str(room.get("occupancy_confidence", "low")).lower()
        noise = str(room.get("automation_noise_likelihood", "high")).lower()
        primary = str(room.get("activity_reason_primary", "")).lower()
        room_role = str(room.get("room_role", "general")).lower()
        recency_band = str(room.get("recency_band", "unknown")).lower()

        include = False

        if occupancy_confidence == "high" and primary == "presence_detected":
            include = True
        elif score >= 55 and noise != "high" and primary in {
            "presence_detected",
            "recent_motion",
            "recent_presence_memory",
        }:
            include = True
        elif score >= 45 and noise == "low" and recency_band in {"fresh", "aging"} and room_role not in {"utility"}:
            include = True

        if room_role in {"transitional", "bathroom"} and primary not in {"presence_detected"}:
            if score < 65:
                include = False

        if include:
            results.append(room)

    return results


def _filter_background_like_rooms(ranked_rooms):
    """
    Keep rooms that are probably active mostly because of automation,
    stale signals, or weak evidence of real human use.
    """
    results = []

    for room in ranked_rooms or []:
        score = int(room.get("human_activity_score", 0))
        occupancy_confidence = str(room.get("occupancy_confidence", "low")).lower()
        noise = str(room.get("automation_noise_likelihood", "low")).lower()
        primary = str(room.get("activity_reason_primary", "")).lower()
        room_role = str(room.get("room_role", "general")).lower()
        recency_band = str(room.get("recency_band", "unknown")).lower()

        background_like = False

        if noise == "high":
            background_like = True
        elif primary in {"background_automation", "lights_only", "access_triggered", "stale_motion"}:
            background_like = True
        elif occupancy_confidence == "low" and score < 35:
            background_like = True
        elif room_role in {"utility"} and primary != "presence_detected":
            background_like = True
        elif room_role in {"transitional", "bathroom"} and recency_band == "stale" and primary != "presence_detected":
            background_like = True

        if background_like:
            results.append(room)

    return results








def _enrich_house_sensor_payload_with_activity_reasons(sensor_payload, now_ts=None):
    """
    Enrich full /ai/house_sensors payload with:
    - SQLite-backed room activity memory updates
    - room reasoning
    - human score
    - recency metadata

    Supports the real live payload shape where:
    sensor_payload["rooms"] is a LIST of room dicts.
    """
    if not isinstance(sensor_payload, dict):
        return sensor_payload

    rooms = sensor_payload.get("rooms")
    if not isinstance(rooms, list):
        return sensor_payload

    _ensure_room_activity_db()

    now_iso = _utc_now_iso()
    enriched_rooms = []

    for room_payload in rooms:
        room_data = dict(room_payload or {})
        room_name = room_data.get("room") or "unknown_room"

        # Normalize nested live room payload into flat signal snapshot
        normalized = _extract_room_signal_snapshot(room_name, room_data)

        # Persist latest live state into SQLite memory
        _upsert_room_activity_state(room_name, room_data, now_iso=now_iso)

        # Compute reasoning from normalized live data + persisted memory
        reasoning = _score_room_intelligence(room_name, normalized, now_ts=now_ts or now_iso)

        # Merge reasoning back into the original room payload
        room_data.update(reasoning)

        enriched_rooms.append(room_data)

    sensor_payload["rooms"] = enriched_rooms
    return sensor_payload





