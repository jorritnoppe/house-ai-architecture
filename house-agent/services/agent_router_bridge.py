from __future__ import annotations

from typing import Any, Dict, Optional

from services.agent_executor import execute_safe_action
from services.agent_service import handle_agent_question
from services.house_ai_history_router import route_history_question
from services.action_auth_service import classify_action_auth
from services.pending_approval_service import get_pending_approval_service


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
        "house state", "house summary", "house overview",
        "house diagnostics", "house status",
        "full house state", "current house state",
    ]):
        return {"type": "route", "target": "/ai/house_state"}

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


def _summarize_house_state(data: dict, action: dict) -> str:
    summary = data.get("summary", {}) or {}
    power_watts = summary.get("current_power_watts")
    crypto_total = summary.get("crypto_total_value")
    telemetry_rooms_seen = summary.get("telemetry_rooms_seen")
    voice_nodes_online = summary.get("voice_nodes_online")

    nodes_health = ((data.get("nodes_health") or {}).get("data") or {})
    warning_nodes = [name for name, item in nodes_health.items() if item.get("status") == "warning"]

    services = data.get("services", {}) or {}
    service_warning_nodes = [
        name for name, item in services.items()
        if item.get("overall_status") not in {"ok", None}
    ]

    audio_effective = (((data.get("audio") or {}).get("effective")) or {})
    audio_active = audio_effective.get("active")
    audio_room = audio_effective.get("effective_target_room")

    parts = []

    if power_watts is not None:
        try:
            kw = round(float(power_watts) / 1000.0, 2)
            if kw >= 0:
                parts.append(f"The house is currently using {kw} kilowatts.")
            else:
                parts.append(f"The house is currently exporting {abs(kw)} kilowatts.")
        except Exception:
            parts.append(f"Current power is {power_watts} watts.")

    if telemetry_rooms_seen is not None:
        parts.append(f"I have recent climate telemetry for {telemetry_rooms_seen} rooms.")

    if crypto_total is not None:
        parts.append(f"Your crypto portfolio is worth {round(float(crypto_total), 2)}.")

    if warning_nodes:
        parts.append(f"Node warnings detected on {', '.join(warning_nodes)}.")
    else:
        parts.append("No node health warnings are currently active.")

    if service_warning_nodes:
        parts.append(f"Service warnings exist on {', '.join(service_warning_nodes)}.")

    if audio_active:
        if audio_room:
            parts.append(f"Audio playback is currently active for {audio_room}.")
        else:
            parts.append("Audio playback is currently active.")
    else:
        parts.append("No audio playback is currently active.")

    if voice_nodes_online is not None:
        parts.append(f"Voice nodes online: {voice_nodes_online}.")

    return " ".join(parts)


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

    if room:
        first = items[0]
        active_count = first.get("binary_on_count", 0)
        state_count = first.get("binary_state_count", 0)
        latest_time = first.get("latest_time") or "unknown time"
        return (
            f"I summarized activity for {room} over the last {minutes} minutes. "
            f"It has {active_count} active items out of {state_count} tracked binary states. "
            f"Latest activity was at {latest_time}."
        )

    preview = []
    for item in items[:5]:
        room_name = item.get("room") or "unknown room"
        active_count = item.get("binary_on_count", 0)
        state_count = item.get("binary_state_count", 0)
        preview.append(f"{room_name}: {active_count} active of {state_count}")

    return (
        f"I summarized room activity for {room_count} rooms over the last {minutes} minutes. "
        f"Examples: {'; '.join(preview)}."
    )


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
