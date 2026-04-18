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


def _join_natural(items: List[str]) -> str:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _opening_greeting(now: datetime) -> str:
    hour = now.hour

    if hour < 12:
        return "Good morning."
    if hour < 18:
        return "Good afternoon."
    return "Good evening."


def _build_house_voice_lines(house: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    energy = _safe_dict(house.get("energy"))
    activity = _safe_dict(house.get("activity"))
    climate = _safe_dict(house.get("climate"))
    infra = _safe_dict(house.get("infrastructure"))

    load_kw = energy.get("estimated_house_load_kw")
    solar_kw = energy.get("solar_power_kw")
    import_kw = energy.get("grid_import_kw")
    export_kw = energy.get("grid_export_kw")
    energy_mode = str(energy.get("mode") or "").strip().lower()

    occupied_rooms = [_human_room_label(x) for x in _safe_list(activity.get("occupied_rooms"))[:6]]
    quiet_now = activity.get("quiet_now")

    min_temp = climate.get("min_temp_c")
    max_temp = climate.get("max_temp_c")
    min_hum = climate.get("min_humidity_percent")
    max_hum = climate.get("max_humidity_percent")

    service_warning_hosts = [_human_room_label(x) if "room" in str(x).lower() else str(x) for x in _safe_list(infra.get("service_warning_hosts"))]
    offline_nodes = [str(x) for x in _safe_list(infra.get("offline_nodes"))]
    monitoring_unavailable = [str(x) for x in _safe_list(infra.get("monitoring_unavailable_nodes"))]

    if load_kw is not None:
        if solar_kw is not None and solar_kw > 0:
            if export_kw is not None and export_kw > 0.05:
                lines.append(
                    f"The house is using about {load_kw:.2f} kilowatts, with solar producing {solar_kw:.2f} kilowatts and exporting {export_kw:.2f} kilowatts."
                )
            elif import_kw is not None and import_kw > 0.05:
                if energy_mode == "stable":
                    lines.append(
                        f"The house is using about {load_kw:.2f} kilowatts. Solar is producing {solar_kw:.2f} kilowatts, with only a small grid import of {import_kw:.2f} kilowatts."
                    )
                else:
                    lines.append(
                        f"The house is using about {load_kw:.2f} kilowatts. Solar is producing {solar_kw:.2f} kilowatts, and the grid is supplying {import_kw:.2f} kilowatts."
                    )
            else:
                lines.append(
                    f"The house is using about {load_kw:.2f} kilowatts, while solar is producing {solar_kw:.2f} kilowatts."
                )
        elif import_kw is not None:
            lines.append(
                f"The house is currently using about {load_kw:.2f} kilowatts, with {import_kw:.2f} kilowatts coming from the grid."
            )

    if occupied_rooms:
        lines.append(
            "The main activity appears to be in " + _join_natural(occupied_rooms) + "."
        )
    else:
        lines.append("No rooms currently show strong occupancy.")

    climate_bits: List[str] = []
    if min_temp is not None and max_temp is not None:
        climate_bits.append(f"temperature is between {min_temp:.1f} and {max_temp:.1f} degrees")
    if min_hum is not None and max_hum is not None:
        climate_bits.append(f"humidity is between {min_hum:.1f} and {max_hum:.1f} percent")

    if climate_bits:
        lines.append("Indoor climate is steady; " + " and ".join(climate_bits) + ".")

    if quiet_now is True:
        lines.append("The house is quiet right now.")
    elif quiet_now is False:
        lines.append("Audio playback is currently active in the house.")

    high_value_warnings: List[str] = []
    if offline_nodes:
        high_value_warnings.append("offline nodes: " + _join_natural(offline_nodes[:3]))
    if service_warning_hosts:
        high_value_warnings.append("service warnings on " + _join_natural(service_warning_hosts[:3]))
    if monitoring_unavailable:
        high_value_warnings.append("monitoring unavailable for " + _join_natural(monitoring_unavailable[:3]))

    if high_value_warnings:
        lines.append("Important house warnings: " + "; ".join(high_value_warnings) + ".")

    return lines


def _build_agenda_voice_lines(agenda: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    today_count = int(agenda.get("today_count") or 0)
    next_item = agenda.get("next_item_text")

    if today_count <= 0:
        return lines

    if today_count == 1:
        if next_item:
            lines.append(f"You have 1 agenda item today. Next: {next_item}.")
        else:
            lines.append("You have 1 agenda item today.")
        return lines

    if next_item:
        lines.append(f"You have {today_count} agenda items today. Next: {next_item}.")
    else:
        lines.append(f"You have {today_count} agenda items today.")

    return lines


def _build_reminder_voice_lines(reminders: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    due_today = int(reminders.get("due_today_count") or 0)
    if due_today <= 0:
        return lines

    if due_today == 1:
        lines.append("You have 1 reminder due today.")
    else:
        lines.append(f"You have {due_today} reminders due today.")

    return lines


def _build_waste_voice_lines(waste: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    if not isinstance(waste, dict):
        return lines

    if waste.get("status") != "ok":
        return lines

    spoken_tomorrow = str(waste.get("spoken_tomorrow") or "").strip()
    spoken_next = str(waste.get("spoken_next") or "").strip()

    if spoken_tomorrow:
        lines.append(f"Reminder. {spoken_tomorrow}")
    elif spoken_next:
        lines.append(spoken_next)

    return lines


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


def _build_spoken_summary(payload: Dict[str, Any]) -> str:
    now = _utc_now()

    house = _safe_dict(payload.get("house"))
    agenda = _safe_dict(payload.get("agenda"))
    reminders = _safe_dict(payload.get("reminders"))
    waste = _safe_dict(payload.get("waste"))

    parts: List[str] = [_opening_greeting(now)]

    parts.extend(_build_house_voice_lines(house))
    parts.extend(_build_waste_voice_lines(waste))
    parts.extend(_build_agenda_voice_lines(agenda))
    parts.extend(_build_reminder_voice_lines(reminders))

    text = " ".join(part.strip() for part in parts if str(part).strip()).strip()
    if text and not text.endswith("."):
        text += "."
    return text or "Good morning. The house summary is available, but no spoken briefing could be generated."


def get_morning_briefing() -> Dict[str, Any]:
    house = get_daily_house_summary()
    waste = get_waste_schedule_summary()

    agenda = {
        "status": "ok",
        "today_count": 0,
        "next_item_text": None,
        "items": [],
    }

    reminders = {
        "status": "ok",
        "due_today_count": 0,
        "items": [],
    }

    warnings = _build_warning_items(house)

    payload = {
        "status": "ok",
        "generated_at": _utc_now_iso(),
        "house": house,
        "waste": waste,
        "agenda": agenda,
        "reminders": reminders,
        "warnings": warnings,
    }
    payload["spoken_summary"] = _build_spoken_summary(payload)
    return payload
