from __future__ import annotations

import re
from typing import Any


ROOM_ALIASES = {
    "entrance": "entranceroom",
    "front door": "entranceroom",
    "doorbird": "entranceroom",
    "hall": "hallwayroom",
    "hallway": "hallwayroom",
    "living": "livingroom",
    "living room": "livingroom",
    "bath": "bathroom",
    "bathroom": "bathroom",
    "toilet": "wcroom",
    "wc": "wcroom",
    "desk": "deskroom",
    "office": "deskroom",
    "desk room": "deskroom",
    "storage": "storageroom",
    "storage room": "storageroom",
    "attic": "attickroom",
    "master bedroom": "masterbedroom",
    "bedroom": "masterbedroom",
    "child room": "childroom",
    "kids room": "childroom",
    "kitchen": "kitchenroom",
    "terrace": "terrasroom",
    "patio": "terrasroom",
}


def _q(question: str) -> str:
    return (question or "").strip().lower()


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


def detect_room(question: str) -> str | None:
    text = _q(question)

    for alias, room in sorted(ROOM_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in text:
            return room

    return None


def detect_minutes(question: str, default_value: int = 60) -> int:
    text = _q(question)

    if "today" in text:
        return 1440
    if "yesterday" in text:
        return 1440
    if "last day" in text:
        return 1440
    if "past day" in text:
        return 1440

    hour_match = re.search(r"(\d+)\s*hour", text)
    if hour_match:
        return max(1, int(hour_match.group(1)) * 60)

    minute_match = re.search(r"(\d+)\s*minute", text)
    if minute_match:
        return max(1, int(minute_match.group(1)))

    if "last hour" in text or "past hour" in text:
        return 60
    if "last 2 hours" in text or "past 2 hours" in text:
        return 120
    if "last 3 hours" in text or "past 3 hours" in text:
        return 180
    if "last 6 hours" in text or "past 6 hours" in text:
        return 360
    if "last 12 hours" in text or "past 12 hours" in text:
        return 720
    if "last 30 minutes" in text or "past 30 minutes" in text:
        return 30
    if "last 15 minutes" in text or "past 15 minutes" in text:
        return 15
    if "last 5 minutes" in text or "past 5 minutes" in text:
        return 5

    return default_value


def route_history_question(question: str) -> dict[str, Any]:
    text = _q(question)
    room = detect_room(question)
    minutes = detect_minutes(question, default_value=60)

    wants_presence = _contains_any(text, [
        "motion", "movement", "presence", "occupied", "occupancy",
        "someone there", "anyone there", "detected"
    ])

    wants_binary_active = _contains_any(text, [
        "currently on", "what is on", "what's on", "currently active",
        "active now", "on right now", "currently enabled"
    ])

    wants_binary_changes = _contains_any(text, [
        "what changed", "changed", "last changed", "recent changes",
        "triggered", "turned on", "turned off", "switched"
    ])

    wants_telemetry = _contains_any(text, [
        "temperature", "humidity", "climate", "telemetry",
        "latest temperature", "latest humidity", "latest climate",
        "power", "solar", "water", "gas", "price"
    ])

    wants_room_summary = _contains_any(text, [
        "room summary", "room activity", "per room", "which rooms",
        "house overview", "overview", "which rooms had activity",
        "rooms had activity", "activity by room"
    ])

    wants_last_change = _contains_any(text, [
        "last change", "latest change", "most recent change",
        "when did", "when was"
    ])

    if wants_room_summary:
        return {
            "status": "ok",
            "tool": "route",
            "target": "/ai/loxone_history_room_activity_ai",
            "params": {
                "minutes": minutes,
                "room": room,
            },
            "reason": "room_activity_query",
        }

    if wants_presence:
        return {
            "status": "ok",
            "tool": "route",
            "target": "/ai/loxone_history_presence_ai",
            "params": {
                "minutes": minutes,
                "room": room,
            },
            "reason": "presence_or_motion_query",
        }

    if wants_binary_active:
        return {
            "status": "ok",
            "tool": "route",
            "target": "/ai/loxone_history_binary_active",
            "params": {
                "minutes": minutes,
                "room": room,
            },
            "reason": "binary_active_query",
        }

    if wants_binary_changes:
        return {
            "status": "ok",
            "tool": "route",
            "target": "/ai/loxone_history_binary_changes",
            "params": {
                "minutes": minutes,
                "room": room,
            },
            "reason": "binary_change_query",
        }

    if wants_telemetry:
        return {
            "status": "ok",
            "tool": "route",
            "target": "/ai/loxone_history_telemetry_latest",
            "params": {
                "minutes": max(minutes, 120),
                "room": room,
            },
            "reason": "telemetry_query",
        }

    if wants_last_change:
        return {
            "status": "ok",
            "tool": "route",
            "target": "/ai/loxone_history_last_change",
            "params": {
                "minutes": minutes,
                "room": room,
            },
            "reason": "last_change_query",
        }

    return {
        "status": "no_match",
        "tool": None,
        "target": None,
        "params": {},
        "reason": "no_history_match",
    }
