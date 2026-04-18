from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparser

from services.google_calendar_service import CalendarConfig, GoogleCalendarService


PRIMARY_CALENDAR_NAME = "jorritnoppe@gmail.com"
LOOKAHEAD_DAYS = 140

WASTE_TYPE_SPOKEN = {
    "rest": "rest waste",
    "paper": "paper",
    "pmd": "PMD",
    "gft": "GFT",
    "glass": "glass",
}



WASTE_KEYWORDS = {
    "rest": [
        "ilva ophaling: huisvuil",
        "huisvuil",
        "restafval",
        "rest afval",
        "rest",
    ],
    "paper": [
        "ilva ophaling: papier",
        "papier",
        "paper",
        "karton",
    ],
    "pmd": [
        "ilva ophaling: pmd",
        "pmd",
    ],
    "gft": [
        "ilva ophaling: gft",
        "gft",
        "groente",
        "fruit",
        "tuinafval",
    ],
    "glass": [
        "ilva ophaling: glas",
        "glas",
        "glass",
    ],
}



def _calendar_service() -> GoogleCalendarService:
    return GoogleCalendarService(
        CalendarConfig(
            credentials_file="/home/jnoppe/house-agent/secrets/google_calendar_credentials.json",
            token_file="/home/jnoppe/house-agent/secrets/google_calendar_token.json",
            timezone_name="Europe/Brussels",
        )
    )


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_event_start(event: Dict[str, Any]) -> Optional[datetime]:
    start = (event.get("start") or {})
    raw = start.get("dateTime") or start.get("date")
    if not raw:
        return None
    dt = dtparser.parse(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _detect_waste_type(text: str) -> str | None:
    t = _safe_lower(text)

    priority = ["rest", "paper", "pmd", "gft", "glass"]

    for waste_type in priority:
        for keyword in WASTE_KEYWORDS[waste_type]:
            if keyword in t:
                return waste_type

    return None



def _human_day_label(dt: datetime, now_local: datetime) -> str:
    event_day = dt.date()
    today = now_local.date()
    tomorrow = today + timedelta(days=1)

    if event_day == today:
        return "today"
    if event_day == tomorrow:
        return "tomorrow"
    return dt.strftime("%A")


def get_waste_schedule_summary(days: int = LOOKAHEAD_DAYS) -> Dict[str, Any]:
    svc = _calendar_service()
    cal_map = svc.get_calendar_map()

    calendar_id = cal_map.get(PRIMARY_CALENDAR_NAME)
    if not calendar_id:
        return {
            "status": "error",
            "message": f"Calendar not found: {PRIMARY_CALENDAR_NAME}",
        }

    now_local = datetime.now().astimezone()
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=days)

    events = svc.events_between(calendar_id, start_local, end_local, max_results=250)

    items: List[Dict[str, Any]] = []

    for event in events:
        summary = str(event.get("summary") or "")
        description = str(event.get("description") or "")
        combined = f"{summary} {description}"

        waste_type = _detect_waste_type(combined)
        if not waste_type:
            continue

        start_dt = _parse_event_start(event)
        if not start_dt:
            continue

        items.append({
            "waste_type": waste_type,
            "summary": summary,
            "start": start_dt.isoformat(),
            "day_label": _human_day_label(start_dt.astimezone(), now_local),
            "all_day": "date" in (event.get("start") or {}),
        })

    items.sort(key=lambda x: x["start"])

    tomorrow_pickups = [x for x in items if x["day_label"] == "tomorrow"]
    next_pickup = items[0] if items else None

    spoken_tomorrow = None
    if tomorrow_pickups:
        names = []
        for x in tomorrow_pickups[:4]:
            wt = x.get("waste_type")
            names.append(WASTE_TYPE_SPOKEN.get(wt, str(wt).upper()))

        if len(names) == 1:
            spoken_tomorrow = f"Tomorrow is {names[0]} pickup."
        elif len(names) == 2:
            spoken_tomorrow = f"Tomorrow is {names[0]} and {names[1]} pickup."
        else:
            spoken_tomorrow = f"Tomorrow is {', '.join(names[:-1])}, and {names[-1]} pickup."

    spoken_next = None
    if next_pickup:
        waste_type = next_pickup.get("waste_type")
        label = WASTE_TYPE_SPOKEN.get(waste_type, str(waste_type).upper())
        day_label = next_pickup.get("day_label") or "unknown day"
        spoken_next = f"The next pickup is {label} on {day_label}."


    return {
        "status": "ok",
        "calendar": PRIMARY_CALENDAR_NAME,
        "count": len(items),
        "items": items,
        "tomorrow_pickups": tomorrow_pickups,
        "next_pickup": next_pickup,
        "spoken_tomorrow": spoken_tomorrow,
        "spoken_next": spoken_next,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
