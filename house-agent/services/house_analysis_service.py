from __future__ import annotations

from typing import Dict

from services.energy_service import energy_service
from services.influx_helpers import iso_now
from services.power_service import (
    get_power_now_data,
    get_energy_today_data,
    get_energy_summary_data,
)
from services.price_service import (
    query_latest_price,
    get_electricity_cost_today,
)
from services.water_service import get_water_softener_overview
from services.apc_service import get_apc_summary_data
from services.loxone_history_service import get_recent_loxone_history
from services.influx_source_map import INFLUX_SOURCE_MAP
from services.house_state_service import get_house_state
from services.house_summary_policy import build_house_summary_facts, rank_house_summary_facts




IGNORED_LOXONE_ROOMS = {"Not Assigned", "unknown", ""}
IGNORED_LOXONE_DOMAINS = set()


def _safe_call(fn, fallback: dict | None = None) -> dict:
    try:
        result = fn()
        if isinstance(result, dict):
            return result
        return fallback or {"status": "error", "message": "Unexpected non-dict result"}
    except Exception as exc:
        return fallback or {"status": "error", "message": str(exc)}


def _human_room_name(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return "unknown room"

    aliases = {
        "masterbedroom": "master bedroom",
        "deskroom": "desk room",
        "entranceroom": "entrance room",
        "livingroom": "living room",
        "childroom": "child room",
        "bathroom": "bathroom",
        "attickroom": "attic room",
        "iotroom": "I O T room",
        "hallwayroom": "hallway",
        "storageroom": "storage room",
        "kitchenroom": "kitchen",
    }
    return aliases.get(raw, raw.replace("_", " "))


def _join_words(items: list[str]) -> str:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _summarize_loxone_recent(minutes: int = 180) -> dict:
    data = _safe_call(lambda: get_recent_loxone_history(minutes=minutes))

    if data.get("status") != "ok":
        return {
            "status": data.get("status", "error"),
            "message": data.get("message", "Unable to read recent Loxone activity"),
            "minutes": minutes,
            "items": [],
            "summary": {
                "rooms_active": [],
                "domains_active": {},
                "change_count": 0,
                "ignored_room_changes": 0,
            },
        }

    items = data.get("items", []) or []

    rooms = {}
    domains = {}
    ignored_room_changes = 0

    for item in items:
        room = str(item.get("room") or "unknown")
        domain = str(item.get("domain") or "unknown")

        if room in IGNORED_LOXONE_ROOMS:
            ignored_room_changes += 1
        else:
            rooms[room] = rooms.get(room, 0) + 1

        if domain not in IGNORED_LOXONE_DOMAINS:
            domains[domain] = domains.get(domain, 0) + 1

    top_rooms = sorted(
        [{"room": room, "changes": count} for room, count in rooms.items()],
        key=lambda x: (-x["changes"], x["room"]),
    )

    return {
        "status": "ok",
        "minutes": minutes,
        "items": items,
        "summary": {
            "rooms_active": top_rooms[:10],
            "domains_active": dict(sorted(domains.items(), key=lambda kv: (-kv[1], kv[0]))),
            "change_count": len(items),
            "ignored_room_changes": ignored_room_changes,
        },
    }


def _build_house_alerts(water: dict) -> list[dict]:
    alerts = []

    salt = ((water.get("salt") or {}) if isinstance(water, dict) else {})
    salt_status = salt.get("salt_level_status")
    if salt_status in {"low", "critical"}:
        alerts.append({
            "type": "salt_level",
            "severity": "warning" if salt_status == "low" else "critical",
            "message": f"Water softener salt level is {salt_status}.",
        })

    refill_warning = water.get("refill_warning") if isinstance(water, dict) else None
    if refill_warning in {"refill_recommended", "urgent_refill"}:
        alerts.append({
            "type": "water_softener_refill",
            "severity": "warning" if refill_warning == "refill_recommended" else "critical",
            "message": refill_warning.replace("_", " "),
        })

    ups_data = (((water.get("ups") if isinstance(water, dict) else None) or {}))
    _ = ups_data  # reserved for later expansion

    return alerts


def _build_brief_lines(facts: dict, mode: str = "today") -> list[str]:
    lines: list[str] = []

    energy_flow = facts.get("energy_flow") or {}
    house_load_kw = energy_flow.get("estimated_house_load_kw")
    solar_power_kw = energy_flow.get("solar_power_kw")
    grid_import_kw = energy_flow.get("grid_import_kw")
    grid_export_kw = energy_flow.get("grid_export_kw")

    if mode == "today":
        if house_load_kw is not None:
            lines.append(f"The house is currently using {round(float(house_load_kw), 2)} kilowatts.")

        energy_today = facts.get("energy_today") or {}
        import_kwh_today = energy_today.get("import_kwh_today")
        export_kwh_today = energy_today.get("export_kwh_today")
        net_kwh_today = energy_today.get("net_kwh_today")

        if import_kwh_today is not None and export_kwh_today is not None:
            lines.append(
                f"Today the house imported {round(float(import_kwh_today), 2)} kilowatt hours and exported {round(float(export_kwh_today), 2)}."
            )
        elif net_kwh_today is not None:
            lines.append(f"Today the net energy usage is {round(float(net_kwh_today), 2)} kilowatt hours.")

        cost_today = facts.get("electricity_cost_today") or {}
        total_cost_eur = cost_today.get("total_cost_eur")
        if total_cost_eur is not None:
            lines.append(f"Electricity cost so far today is {round(float(total_cost_eur), 2)} euro.")

        solar_today = facts.get("solar_today") or {}
        daily_energy_kwh = solar_today.get("daily_energy_kwh")
        if daily_energy_kwh is not None:
            lines.append(f"Solar production today is {round(float(daily_energy_kwh), 2)} kilowatt hours.")
    else:
        price_now = ((facts.get("electricity_price_now") or {}).get("data") or {})
        price_value = price_now.get("value")
        if price_value is not None:
            lines.append(f"The current electricity price is {round(float(price_value), 3)} euro per kilowatt hour.")

        # Real-time house load / solar / grid flow are now handled by the shared
        # canonical house-state summary, so we intentionally do not repeat them here.

    water_softener = facts.get("water_softener") or {}
    flow = water_softener.get("flow") or {}
    salt = water_softener.get("salt") or {}

    if flow.get("status") == "ok":
        flow_lpm = flow.get("flow_lpm")
        if flow.get("flow_active") and flow_lpm is not None:
            lines.append(f"Water is currently flowing at {round(float(flow_lpm), 2)} liters per minute.")

    if salt.get("status") == "ok":
        salt_pct = salt.get("salt_level_percent")
        salt_status = salt.get("salt_level_status")
        if salt_pct is not None and salt_status:
            lines.append(f"Water softener salt level is {salt_status} at {round(float(salt_pct), 1)} percent.")

    loxone_key = "loxone_activity_today" if mode == "today" else "loxone_recent_activity"
    loxone_summary = ((facts.get(loxone_key) or {}).get("summary") or {})
    rooms_active = loxone_summary.get("rooms_active") or []
    if rooms_active:
        room_names = [_human_room_name(x.get("room")) for x in rooms_active[:3]]
        room_text = _join_words(room_names)
        if room_text:
            prefix = "The most active rooms today were" if mode == "today" else "The most active rooms recently were"
            lines.append(f"{prefix} {room_text}.")

    alerts = facts.get("alerts") or []
    if alerts:
        alert_messages = [str(a.get("message")) for a in alerts if a.get("message")]
        if alert_messages:
            lines.append(f"Alerts: {' '.join(alert_messages)}")

    if not lines:
        lines.append("House summary is available, but there is not enough data yet for a detailed briefing.")

    return lines





def get_house_facts_now() -> Dict[str, object]:
    power_now = _safe_call(get_power_now_data)
    energy_summary = _safe_call(get_energy_summary_data)
    energy_snapshot = _safe_call(energy_service.get_live_snapshot)
    energy_flow = _safe_call(energy_service.get_power_flow_summary)
    latest_price = _safe_call(lambda: query_latest_price(range_window="-7d"), fallback={"status": "no_data"})
    water = _safe_call(get_water_softener_overview)
    apc = _safe_call(get_apc_summary_data)
    loxone_recent = _summarize_loxone_recent(minutes=180)

    solar_now = {}
    if energy_snapshot.get("status") in {"ok", "partial", "degraded"}:
        solar_now = energy_snapshot.get("sma", {}) or {}
    if not solar_now:
        solar_now = {"status": "error", "message": "No unified solar snapshot available"}

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "source_map_keys": sorted(list(INFLUX_SOURCE_MAP.keys())),
        "power_now": power_now,
        "energy_summary": energy_summary,
        "energy_snapshot": energy_snapshot,
        "energy_flow": energy_flow,
        "electricity_price_now": {
            "status": "ok" if latest_price else "no_data",
            "data": latest_price,
        },
        "solar_now": solar_now,
        "water_softener": water,
        "ups": apc,
        "loxone_recent_activity": {
            "status": loxone_recent.get("status", "error"),
            "minutes": loxone_recent.get("minutes", 180),
            "summary": loxone_recent.get("summary", {}),
        },
        "alerts": [],
    }


def get_house_facts_today() -> Dict[str, object]:
    power_now = _safe_call(get_power_now_data)
    energy_today = _safe_call(get_energy_today_data)
    energy_summary = _safe_call(get_energy_summary_data)
    energy_snapshot = _safe_call(energy_service.get_live_snapshot)
    energy_flow = _safe_call(energy_service.get_power_flow_summary)
    cost_today = _safe_call(get_electricity_cost_today)
    water = _safe_call(get_water_softener_overview)
    apc = _safe_call(get_apc_summary_data)
    loxone_recent = _summarize_loxone_recent(minutes=1440)

    solar_today = {}
    if energy_snapshot.get("status") in {"ok", "partial", "degraded"}:
        solar_today = energy_snapshot.get("sma", {}) or {}
    if not solar_today:
        solar_today = {"status": "error", "message": "No unified solar snapshot available"}

    alerts = _build_house_alerts(water)

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "source_map_keys": sorted(list(INFLUX_SOURCE_MAP.keys())),
        "power_now": power_now,
        "energy_summary": energy_summary,
        "energy_snapshot": energy_snapshot,
        "energy_flow": energy_flow,
        "energy_today": energy_today,
        "electricity_cost_today": cost_today,
        "solar_today": solar_today,
        "water_softener": water,
        "ups": apc,
        "loxone_activity_today": {
            "status": loxone_recent.get("status", "error"),
            "minutes": loxone_recent.get("minutes", 1440),
            "summary": loxone_recent.get("summary", {}),
        },
        "alerts": alerts,
    }

def _build_house_state_brief_lines() -> list[str]:
    try:
        house_state = get_house_state()
        if not isinstance(house_state, dict) or house_state.get("status") != "ok":
            return []

        facts = build_house_summary_facts(house_state, mode="briefing")
        facts = rank_house_summary_facts(facts, mode="briefing")

        lines = []
        seen = set()

        for fact in facts:
            message = (fact.get("message") or "").strip()
            if not message:
                continue
            if message in seen:
                continue
            seen.add(message)
            lines.append(message)

        return lines
    except Exception:
        return []



def get_house_briefing_now() -> Dict[str, object]:
    facts = get_house_facts_now()
    shared_lines = _build_house_state_brief_lines()
    legacy_lines = _build_brief_lines(facts, mode="now")

    lines = []
    seen = set()

    for line in shared_lines + legacy_lines:
        text = (line or "").strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        lines.append(text)

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "spoken": " ".join(lines),
        "lines": lines,
        "facts": facts,
    }


def get_house_briefing_today() -> Dict[str, object]:
    facts = get_house_facts_today()
    lines = _build_brief_lines(facts, mode="today")

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "spoken": " ".join(lines),
        "lines": lines,
        "facts": facts,
    }
