from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests
from flask import Blueprint, jsonify, request

from services.google_calendar_service import CalendarConfig, GoogleCalendarService
from services.speaker_router_service import normalize_speaker, speak_text







agenda_bp = Blueprint("agenda", __name__)

CALENDAR_CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CALENDAR_CREDENTIALS_FILE",
    "/opt/house-ai/secrets/google_calendar_credentials.json",
)
CALENDAR_TOKEN_FILE = os.environ.get(
    "GOOGLE_CALENDAR_TOKEN_FILE",
    "/opt/house-ai/secrets/google_calendar_token.json",
)

service = GoogleCalendarService(
    CalendarConfig(
        credentials_file=CALENDAR_CREDENTIALS_FILE,
        token_file=CALENDAR_TOKEN_FILE,
        timezone_name="Europe/Brussels",
    )
)

def _get_agenda_briefing_text() -> str:
    briefing = requests.get("http://127.0.0.1:8000/agenda/briefing", timeout=10).json()
    return briefing.get("spoken", "There are no house agenda items scheduled for today.")



def _normalize_player_id(payload: dict) -> str:
    raw = (
        payload.get("player_id")
        or payload.get("target")
        or payload.get("speaker")
        or "desk"
    )
    key = str(raw).strip().lower()

    aliases = {
        "desk": "desk",
        "desktop": "desk",
        "living": "living",
        "livingroom": "living",
        "living_room": "living",
        "living area": "living",
        "livingarea": "living",
        "wc": "wc",
        "toilet": "wc",
        "bathroom": "bathroom",
    }
    return aliases.get(key, key)


def _get_agenda_briefing_text() -> str:
    briefing = requests.get("http://127.0.0.1:8000/agenda/briefing", timeout=10).json()
    return briefing.get("spoken", "There are no house agenda items scheduled for today.")



@agenda_bp.post("/agenda/announce_and_speak")
def agenda_announce_and_speak():
    payload = request.get_json(silent=True) or {}

    spoken = _get_agenda_briefing_text()
    speaker = normalize_speaker(
        payload.get("player_id") or payload.get("target") or payload.get("speaker")
    )
    level = (payload.get("level") or "attention").strip().lower()
    volume = payload.get("volume")

    try:
        routed = speak_text(
            text=spoken,
            speaker=speaker,
            level=level,
            volume=volume,
        )
        return jsonify(
            {
                "status": "ok",
                "spoken": spoken,
                "player_id": speaker,
                "level": level,
                "voice_result": routed["result"],
                "route_mode": routed["mode"],
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "status": "error",
                "spoken": spoken,
                "player_id": speaker,
                "level": level,
                "error": str(exc),
            }
        ), 500






@agenda_bp.get("/agenda/briefing")
def agenda_briefing():
    spoken_data = requests.get("http://127.0.0.1:8000/agenda/spoken", timeout=10).json()

    power_text = ""
    try:
        power_data = requests.get("http://127.0.0.1:8000/ai/power_now", timeout=10).json()
        watts = power_data.get("power_watts")
        if watts is not None:
            kw = round(float(watts) / 1000.0, 1)
            power_text = f" The house is currently using {kw} kilowatts."
    except Exception:
        power_text = ""

    spoken = spoken_data.get("spoken", "There are no house agenda items scheduled for today.")
    final_text = spoken + power_text

    return jsonify(
        {
            "status": "ok",
            "spoken": final_text,
            "agenda": spoken_data,
        }
    )



@agenda_bp.post("/agenda/automation/laundry_finished")
def agenda_automation_laundry_finished():
    now = datetime.now().astimezone()
    start_dt = now
    end_dt = now + timedelta(minutes=15)

    event = service.create_event(
        calendar_id=service.get_calendar_map()["Laundry"],
        summary="[TASK][LAUNDRY][LAUNDRY] Move laundry to dryer",
        start_dt=start_dt,
        end_dt=end_dt,
        description="source: washer automation",
    )

    return jsonify({"status": "ok", "event": event})




@agenda_bp.get("/agenda/status")
def agenda_status():
    return jsonify(
        {
            "status": "ok",
            "credentials_file_exists": os.path.exists(CALENDAR_CREDENTIALS_FILE),
            "token_file_exists": os.path.exists(CALENDAR_TOKEN_FILE),
        }
    )


@agenda_bp.get("/agenda/calendars")
def agenda_calendars():
    items = service.list_calendars()
    return jsonify(
        {
            "status": "ok",
            "count": len(items),
            "items": [
                {
                    "id": x.get("id"),
                    "summary": x.get("summary"),
                    "primary": x.get("primary", False),
                    "accessRole": x.get("accessRole"),
                }
                for x in items
            ],
        }
    )






@agenda_bp.post("/agenda/announce")
def agenda_announce():
    payload = request.get_json(silent=True) or {}

    spoken = _get_agenda_briefing_text()
    speaker = normalize_speaker(
        payload.get("player_id") or payload.get("target") or payload.get("speaker")
    )
    level = (payload.get("level") or "attention").strip().lower()
    volume = payload.get("volume")

    try:
        routed = speak_text(
            text=spoken,
            speaker=speaker,
            level=level,
            volume=volume,
        )
        return jsonify(
            {
                "status": "ok",
                "spoken": spoken,
                "player_id": speaker,
                "level": level,
                "voice_result": routed["result"],
                "route_mode": routed["mode"],
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "status": "error",
                "spoken": spoken,
                "player_id": speaker,
                "level": level,
                "error": str(exc),
            }
        ), 500






@agenda_bp.get("/agenda/today")
def agenda_today():
    requested = request.args.getlist("calendar")
    cal_map = service.get_calendar_map()

    if requested:
        selected = {name: cal_map[name] for name in requested if name in cal_map}
    else:
        preferred = [
            "House Task",
            "Cleaning",
            "Laundry",
            "Plants",
            "Maintenance",
            "Ai Suggestions",
            "AI Suggestions",
        ]
        selected = {name: cal_map[name] for name in preferred if name in cal_map}

    raw = service.get_today(list(selected.values()))

    items = []
    for cal_name, cal_id in selected.items():
        for event in raw.get(cal_id, []):
            start = event.get("start", {})
            end = event.get("end", {})
            items.append(
                {
                    "calendar": cal_name,
                    "calendar_id": cal_id,
                    "id": event.get("id"),
                    "summary": event.get("summary"),
                    "description": event.get("description", ""),
                    "status": event.get("status"),
                    "htmlLink": event.get("htmlLink"),
                    "start": start.get("dateTime") or start.get("date"),
                    "end": end.get("dateTime") or end.get("date"),
                    "all_day": "date" in start,
                }
            )

    items.sort(key=lambda x: (x["start"] or "", x["calendar"], x["summary"] or ""))

    return jsonify(
        {
            "status": "ok",
            "count": len(items),
            "items": items,
        }
    )


@agenda_bp.get("/agenda/summary")
def agenda_summary():
    requested = request.args.getlist("calendar")
    cal_map = service.get_calendar_map()

    if requested:
        selected = {name: cal_map[name] for name in requested if name in cal_map}
    else:
        preferred = [
            "House Task",
            "Cleaning",
            "Laundry",
            "Plants",
            "Maintenance",
            "Ai Suggestions",
            "AI Suggestions",
        ]
        selected = {name: cal_map[name] for name in preferred if name in cal_map}

    raw = service.get_today(list(selected.values()))

    grouped = {}
    total = 0

    for cal_name, cal_id in selected.items():
        grouped[cal_name] = []
        for event in raw.get(cal_id, []):
            start = event.get("start", {})
            grouped[cal_name].append(
                {
                    "summary": event.get("summary"),
                    "start": start.get("dateTime") or start.get("date"),
                    "all_day": "date" in start,
                }
            )
            total += 1

    spoken_lines = []
    if total == 0:
        spoken = "There are no house agenda items scheduled for today."
    else:
        spoken_lines.append(f"There are {total} house agenda items for today.")
        for cal_name, entries in grouped.items():
            if entries:
                spoken_lines.append(f"{cal_name}: {len(entries)} item{'s' if len(entries) != 1 else ''}.")
        spoken = " ".join(spoken_lines)

    return jsonify(
        {
            "status": "ok",
            "total_items": total,
            "grouped": grouped,
            "spoken_summary": spoken,
        }
    )


@agenda_bp.get("/agenda/spoken")
def agenda_spoken():
    requested = request.args.getlist("calendar")
    cal_map = service.get_calendar_map()

    if requested:
        selected = {name: cal_map[name] for name in requested if name in cal_map}
    else:
        preferred = [
            "House Task",
            "Cleaning",
            "Laundry",
            "Plants",
            "Maintenance",
            "Ai Suggestions",
            "AI Suggestions",
        ]
        selected = {name: cal_map[name] for name in preferred if name in cal_map}

    raw = service.get_today(list(selected.values()))

    total = 0
    spoken_parts = []

    for cal_name, cal_id in selected.items():
        entries = raw.get(cal_id, [])
        if entries:
            total += len(entries)
            spoken_parts.append(f"{cal_name}: {len(entries)}")

    if total == 0:
        spoken = "There are no house agenda items scheduled for today."
    else:
        spoken = "Today on the house agenda: " + ", ".join(spoken_parts) + "."

    return jsonify(
        {
            "status": "ok",
            "spoken": spoken,
            "total_items": total,
        }
    )


@agenda_bp.post("/agenda/task/cleaning")
def agenda_task_cleaning():
    payload = request.get_json(force=True)
    summary = payload["summary"]
    description = payload.get("description", "source: house-agent")
    day_str = payload["day"]

    day = service.parse_dt(day_str)
    cal_map = service.get_calendar_map()
    calendar_id = cal_map["Cleaning"]

    event = service.create_all_day_task(
        calendar_id=calendar_id,
        summary=summary,
        day=day,
        description=description,
    )
    return jsonify({"status": "ok", "event": event})


@agenda_bp.post("/agenda/task/laundry")
def agenda_task_laundry():
    payload = request.get_json(force=True)
    summary = payload["summary"]
    description = payload.get("description", "source: house-agent")
    day_str = payload.get("day")
    start_str = payload.get("start")
    end_str = payload.get("end")

    cal_map = service.get_calendar_map()
    calendar_id = cal_map["Laundry"]

    if day_str:
        day = service.parse_dt(day_str)
        event = service.create_all_day_task(
            calendar_id=calendar_id,
            summary=summary,
            day=day,
            description=description,
        )
    else:
        start_dt = service.parse_dt(start_str)
        end_dt = service.parse_dt(end_str)
        event = service.create_event(
            calendar_id=calendar_id,
            summary=summary,
            start_dt=start_dt,
            end_dt=end_dt,
            description=description,
        )

    return jsonify({"status": "ok", "event": event})


@agenda_bp.post("/agenda/task/plants")
def agenda_task_plants():
    payload = request.get_json(force=True)
    summary = payload["summary"]
    description = payload.get("description", "source: house-agent")
    day = service.parse_dt(payload["day"])

    cal_map = service.get_calendar_map()
    calendar_id = cal_map["Plants"]

    event = service.create_all_day_task(
        calendar_id=calendar_id,
        summary=summary,
        day=day,
        description=description,
    )
    return jsonify({"status": "ok", "event": event})


@agenda_bp.post("/agenda/task/maintenance")
def agenda_task_maintenance():
    payload = request.get_json(force=True)
    summary = payload["summary"]
    description = payload.get("description", "source: house-agent")
    day = service.parse_dt(payload["day"])

    cal_map = service.get_calendar_map()
    calendar_id = cal_map["Maintenance"]

    event = service.create_all_day_task(
        calendar_id=calendar_id,
        summary=summary,
        day=day,
        description=description,
    )
    return jsonify({"status": "ok", "event": event})





@agenda_bp.post("/agenda/event")
def agenda_create_event():
    payload = request.get_json(force=True)

    calendar_name = payload["calendar"]
    summary = payload["summary"]
    description = payload.get("description", "")
    all_day = bool(payload.get("all_day", False))

    cal_map = service.get_calendar_map()
    if calendar_name not in cal_map:
        return jsonify(
            {"status": "error", "error": f"Unknown calendar: {calendar_name}"}
        ), 400

    calendar_id = cal_map[calendar_name]

    if all_day:
        day_str = payload.get("day")
        if not day_str:
            return jsonify({"status": "error", "error": "Missing 'day'"}), 400
        day = service.parse_dt(day_str)
        event = service.create_all_day_task(
            calendar_id=calendar_id,
            summary=summary,
            day=day,
            description=description,
        )
    else:
        start_dt = service.parse_dt(payload["start"])
        end_dt = service.parse_dt(payload["end"])
        event = service.create_event(
            calendar_id=calendar_id,
            summary=summary,
            start_dt=start_dt,
            end_dt=end_dt,
            description=description,
        )

    return jsonify({"status": "ok", "event": event})
