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


ROOM_ACTIVITY_DB_PATH = os.environ.get(
    "HOUSE_ROOM_ACTIVITY_DB_PATH",
    "/home/jnoppe/house-agent/data/room_activity_state.db",
)

_ROOM_ACTIVITY_DB_LOCK = threading.Lock()


def _safe_bool(value: Any) -> bool:
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_any_timestamp(value):
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
    db_dir = os.path.dirname(ROOM_ACTIVITY_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(ROOM_ACTIVITY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_room_activity_db():
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
    return (room_name or "").strip().lower().replace(" ", "_")


def _extract_room_signal_snapshot(room_name, room_payload):
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

    access_times = []
    for item in active_access_signals + status_signals:
        if isinstance(item, dict):
            ts = item.get("time")
            if ts:
                access_times.append(ts)

    if access_times:
        normalized["last_access_at"] = max(access_times)

    return normalized


def _normalize_room_role(room_name, room_payload):
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


def _get_room_zone(room_name: str) -> str:
    name = str(room_name or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")

    if not name:
        return "outside_misc"
    if "upstair" in name:
        return "upstairs"
    if "downstair" in name:
        return "downstairs"
    if name in {"bathroom", "deskroom", "childroom", "masterbedroom", "hallwayroom"}:
        return "upstairs"
    if name in {"attickroom", "atticroom"}:
        return "attic"
    if name in {"livingroom", "kitchenroom", "diningroom", "entranceroom", "storageroom", "wcroom"}:
        return "downstairs"

    return "outside_misc"


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


def _join_natural(items):
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


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
    payload = room_payload or {}
    profile = _get_room_role_profile(room_name, payload)
    recency = _build_room_recency_snapshot(room_name, payload, now_ts=now_ts)
    reason_info = _analyze_room_activity_reason(room_name, payload, now_ts=now_ts)

    presence = _safe_bool(payload.get("presence"))
    motion = _safe_bool(payload.get("motion"))
    lights_on = _safe_bool(payload.get("lights_on") or payload.get("light_on") or payload.get("lighting_active"))
    access_active = _safe_bool(payload.get("door_open") or payload.get("door_active") or payload.get("nfc_active") or payload.get("access_active"))
    climate_active = _safe_bool(payload.get("climate_active") or payload.get("heating_active") or payload.get("hvac_active") or payload.get("temperature_control_active"))

    base_score = 0.0

    if presence:
        base_score += 65.0 * profile["presence_weight"]
    elif recency["presence_decay_factor"] > 0.60 and recency["presence_age_seconds"] is not None:
        base_score += 18.0 * profile["presence_weight"] * recency["presence_decay_factor"]

    if motion:
        base_score += 24.0 * profile["motion_weight"]
    elif recency["motion_age_seconds"] is not None:
        base_score += 14.0 * profile["motion_weight"] * recency["motion_decay_factor"]

    if lights_on:
        base_score += 10.0 * profile["light_weight"]
    elif recency["light_age_seconds"] is not None and recency["light_decay_factor"] > 0.55:
        base_score += 4.0 * profile["light_weight"] * recency["light_decay_factor"]

    if access_active:
        base_score += 8.0 * profile["access_weight"]
    elif recency["access_age_seconds"] is not None and recency["access_decay_factor"] > 0.60:
        base_score += 3.0 * profile["access_weight"] * recency["access_decay_factor"]

    if climate_active:
        base_score += 4.0 * profile["climate_weight"]
    elif recency["climate_age_seconds"] is not None and recency["climate_decay_factor"] > 0.65:
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


def _filter_human_likely_rooms(ranked_rooms):
    results = []

    for room in ranked_rooms or []:
        classification = str(room.get("classification", "")).lower()
        confidence_score = float(room.get("confidence_score", 0.0) or 0.0)
        human_likelihood = float(room.get("human_likelihood", 0.0) or 0.0)
        automation_likelihood = float(room.get("automation_likelihood", 0.0) or 0.0)
        room_role = str(room.get("room_role", "general")).lower()

        include = False

        if classification == "occupied" and confidence_score >= 0.60:
            include = True
        elif classification == "transient" and human_likelihood >= 0.58 and confidence_score >= 0.52:
            include = True
        elif classification == "uncertain" and human_likelihood >= 0.62 and automation_likelihood <= 0.42:
            include = True

        if room_role in {"utility"} and classification != "occupied":
            include = False

        if include:
            results.append(room)

    return results


def _filter_background_like_rooms(ranked_rooms):
    results = []

    for room in ranked_rooms or []:
        classification = str(room.get("classification", "")).lower()
        confidence_score = float(room.get("confidence_score", 0.0) or 0.0)
        human_likelihood = float(room.get("human_likelihood", 0.0) or 0.0)
        automation_likelihood = float(room.get("automation_likelihood", 0.0) or 0.0)
        room_role = str(room.get("room_role", "general")).lower()

        include = False

        if classification == "passive":
            include = True
        elif automation_likelihood >= 0.62 and human_likelihood <= 0.42:
            include = True
        elif classification == "idle" and room_role == "utility" and confidence_score >= 0.65:
            include = True
        elif room_role in {"utility"} and classification in {"uncertain", "passive"}:
            include = True

        if include:
            results.append(room)

    return results


def _build_ranked_room_intelligence(sensor_payload):
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


def _enrich_house_sensor_payload_with_activity_reasons(sensor_payload, now_ts=None):
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

        normalized = _extract_room_signal_snapshot(room_name, room_data)
        _upsert_room_activity_state(room_name, room_data, now_iso=now_iso)
        reasoning = _score_room_intelligence(room_name, normalized, now_ts=now_ts or now_iso)
        room_data.update(reasoning)
        enriched_rooms.append(room_data)

    sensor_payload["rooms"] = enriched_rooms
    return sensor_payload


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

    if any(x in q for x in [
        "is anyone downstairs",
        "anyone downstairs",
        "is anyone upstairs",
        "anyone upstairs",
        "is anyone in the attic",
        "anyone in the attic",
        "which rooms downstairs are occupied",
        "what rooms downstairs are occupied",
        "which downstairs rooms are occupied",
        "what downstairs rooms are occupied",
        "which rooms upstairs are occupied",
        "what rooms upstairs are occupied",
        "which upstairs rooms are occupied",
        "what upstairs rooms are occupied",
        "which rooms downstairs are being used",
        "what rooms downstairs are being used",
        "which downstairs rooms are being used",
        "what downstairs rooms are being used",
        "which rooms upstairs are being used",
        "what rooms upstairs are being used",
        "which upstairs rooms are being used",
        "what upstairs rooms are being used",
        "attic occupancy",
        "upstairs occupancy",
        "downstairs occupancy",
    ]):
        return {
            "type": "route",
            "target": "/ai/house_sensors",
            "params": {"minutes": 60, "limit": 8000},
            "reason": "zone_occupancy_query",
        }

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

    if any(x in q for x in [
        "morning briefing",
        "give me my morning briefing",
        "good morning",
        "morning summary",
        "today briefing",
    ]):
        return {
            "type": "route",
            "target": "/ai/morning_briefing",
            "params": {},
            "reason": "morning_briefing_query",
        }

    if any(x in q for x in [
        "evening briefing",
        "give me my evening briefing",
        "tonight briefing",
        "evening summary",
        "night briefing",
        "what should i know for tonight",
    ]):
        return {
            "type": "route",
            "target": "/ai/evening_briefing",
            "params": {},
            "reason": "evening_briefing_query",
        }

    if any(x in q for x in [
        "waste schedule",
        "garbage schedule",
        "trash schedule",
        "bin schedule",
        "pickup schedule",
        "waste pickup",
        "garbage pickup",
        "trash pickup",
        "when is the next pickup",
        "what is the next pickup",
        "is there garbage tomorrow",
        "is waste being collected tomorrow",
        "what bin goes out tomorrow",
        "what garbage goes out tomorrow",
        "what waste goes out tomorrow",
    ]):
        return {
            "type": "route",
            "target": "/ai/waste_schedule_summary",
            "params": {},
            "reason": "waste_schedule_query",
        }

    if any(x in q for x in [
        "daily house summary",
        "house briefing",
        "daily briefing",
        "morning house briefing",
        "morning house summary",
        "summarize the house",
        "summarize current house status",
        "current house status",
        "house status",
        "house summary",
        "give me the house briefing",
        "give me a house briefing",
        "give me a house summary",
        "give me the house summary",
    ]):
        return {
            "type": "route",
            "target": "/ai/daily_house_summary",
            "params": {},
            "reason": "daily_house_summary_query",
        }

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
        "lights on",
        "which lights are on",
        "what lights are on",
        "active lights",
        "lighting active",
        "active motion",
        "where is motion",
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
        "why is the",
        "why is ",
        "which room is most active",
        "what room is most active",
        "which room seems most active",
        "what room seems most active",
        "which room seems most active right now",
        "what room seems most active right now",
        "most active room",
        "most important active room",
        "which rooms are likely being used",
        "what rooms are likely being used",
        "likely human active rooms",
        "likely occupied rooms",
        "rooms likely in use",
        "which rooms were recently used by a person",
        "what rooms were recently used by a person",
        "recently used by a person",
        "recent human activity",
        "which rooms had recent human activity",
        "what rooms had recent human activity",
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
            "params": {"minutes": 60, "limit": 8000},
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

    return None



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
        room_name = item.get("room") or "unknown"
        state_key = item.get("state_key")
        key = (room_name, state_key)
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
            try:
                parts.append(f"temp {round(float(temp), 1)} C")
            except Exception:
                pass
        if hum is not None:
            try:
                parts.append(f"humidity {round(float(hum), 1)} percent")
            except Exception:
                pass

        if len(parts) > 1:
            preview.append(", ".join(parts))

    if not preview:
        return f"I found no recent temperature or humidity telemetry for {scope} in the last {minutes} minutes."

    return (
        f"I found recent house climate telemetry for {len(grouped)} rooms in {scope} "
        f"over the last {minutes} minutes. {'; '.join(preview)}."
    )





def _summarize_waste_schedule(data: dict, action: dict) -> str:
    if not isinstance(data, dict):
        return "I could not read the waste schedule."

    spoken_tomorrow = str(data.get("spoken_tomorrow") or "").strip()
    spoken_next = str(data.get("spoken_next") or "").strip()
    next_pickup = data.get("next_pickup") or {}
    tomorrow_pickups = data.get("tomorrow_pickups") or []

    if spoken_tomorrow:
        if spoken_next:
            return f"{spoken_tomorrow} {spoken_next}"
        return spoken_tomorrow

    if spoken_next:
        return spoken_next

    if tomorrow_pickups:
        return "There is waste pickup tomorrow."

    if next_pickup:
        waste_type = next_pickup.get("waste_type") or "waste"
        day_label = next_pickup.get("day_label") or "an upcoming day"
        return f"The next pickup is {waste_type} on {day_label}."

    return "I could not find any upcoming waste pickup events."




def _build_answer_from_safe_result(action, result, question: str = ""):
    if result.get("status") != "ok":
        return "I could not complete that request."

    data = result.get("data", {}) or {}
    target = action.get("target", "")

    if target == "/ai/house_sensors":
        return _summarize_house_sensors(data, action, question=question)

    if target == "/ai/loxone_history_telemetry_latest":
        return _summarize_history_telemetry(data, action)

    if target == "/ai/waste_schedule_summary":
        return _summarize_waste_schedule(data, action)

    if target == "/ai/morning_briefing":
        spoken = data.get("spoken_summary")
        if spoken:
            return spoken
        return "I retrieved the morning briefing, but could not render the spoken summary."

    if target == "/ai/evening_briefing":
        spoken = data.get("spoken_summary")
        if spoken:
            return spoken
        return "I retrieved the evening briefing, but could not render the spoken summary."

    if target == "/ai/daily_house_summary":
        spoken = data.get("spoken_summary")
        if spoken:
            return spoken
        return "I retrieved the daily house summary, but could not render the spoken summary."

    return "I found some data, but I could not summarize it yet."




def _summarize_house_sensors(sensor_result, action=None, question=None, user_question=None):
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

    def _rooms_in_zone(zone_name: str):
        return [
            room
            for room in ranked_rooms
            if _get_room_zone(room.get("room_name") or room.get("room")) == zone_name
        ]

    def _occupied_rooms_in_zone(zone_name: str):
        return [
            room
            for room in _rooms_in_zone(zone_name)
            if str(room.get("classification", "")).lower() == "occupied"
        ]

    def _human_rooms_in_zone(zone_name: str):
        return [
            room
            for room in human_rooms
            if _get_room_zone(room.get("room_name") or room.get("room")) == zone_name
        ]

    def _room_names(items, limit=6):
        return [r.get("room_name") or r.get("room") or "unknown room" for r in items[:limit]]

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

    if "downstairs" in actual_question:
        downstairs_occupied = _occupied_rooms_in_zone("downstairs")
        downstairs_human = _human_rooms_in_zone("downstairs")

        if any(x in actual_question for x in ["is anyone downstairs", "anyone downstairs"]):
            if downstairs_occupied:
                return (
                    "Yes, downstairs currently appears occupied. "
                    "The most likely occupied downstairs rooms are: "
                    + ", ".join(_room_names(downstairs_occupied, limit=5))
                    + "."
                )
            if downstairs_human:
                return (
                    "Downstairs shows likely human activity in: "
                    + ", ".join(_room_names(downstairs_human, limit=5))
                    + "."
                )
            return "I do not currently see strong signs of downstairs occupancy."

        if any(
            x in actual_question
            for x in [
                "which rooms downstairs are occupied",
                "what rooms downstairs are occupied",
                "which downstairs rooms are occupied",
                "what downstairs rooms are occupied",
                "which rooms downstairs are being used",
                "what rooms downstairs are being used",
                "which downstairs rooms are being used",
                "what downstairs rooms are being used",
            ]
        ):
            if downstairs_occupied:
                return (
                    "The downstairs rooms that currently look occupied are: "
                    + ", ".join(_room_names(downstairs_occupied, limit=6))
                    + "."
                )
            if downstairs_human:
                return (
                    "The downstairs rooms most likely being used are: "
                    + ", ".join(_room_names(downstairs_human, limit=6))
                    + "."
                )
            return "I do not currently see occupied downstairs rooms."

    if "upstairs" in actual_question:
        upstairs_occupied = _occupied_rooms_in_zone("upstairs")
        upstairs_human = _human_rooms_in_zone("upstairs")

        if any(x in actual_question for x in ["is anyone upstairs", "anyone upstairs"]):
            if upstairs_occupied:
                return (
                    "Yes, upstairs currently appears occupied. "
                    "The most likely occupied upstairs rooms are: "
                    + ", ".join(_room_names(upstairs_occupied, limit=5))
                    + "."
                )
            if upstairs_human:
                return (
                    "Upstairs shows likely human activity in: "
                    + ", ".join(_room_names(upstairs_human, limit=5))
                    + "."
                )
            return "I do not currently see strong signs of upstairs occupancy."

        if any(
            x in actual_question
            for x in [
                "which rooms upstairs are occupied",
                "what rooms upstairs are occupied",
                "which upstairs rooms are occupied",
                "what upstairs rooms are occupied",
                "which rooms upstairs are being used",
                "what rooms upstairs are being used",
                "which upstairs rooms are being used",
                "what upstairs rooms are being used",
            ]
        ):
            if upstairs_occupied:
                return (
                    "The upstairs rooms that currently look occupied are: "
                    + ", ".join(_room_names(upstairs_occupied, limit=6))
                    + "."
                )
            if upstairs_human:
                return (
                    "The upstairs rooms most likely being used are: "
                    + ", ".join(_room_names(upstairs_human, limit=6))
                    + "."
                )
            return "I do not currently see occupied upstairs rooms."

    if "attic" in actual_question:
        attic_occupied = _occupied_rooms_in_zone("attic")
        attic_human = _human_rooms_in_zone("attic")

        if any(x in actual_question for x in ["is anyone in the attic", "is anyone attic", "anyone in the attic"]):
            if attic_occupied:
                return (
                    "Yes, the attic currently appears occupied. Active attic rooms: "
                    + ", ".join(_room_names(attic_occupied, limit=3))
                    + "."
                )
            if attic_human:
                return (
                    "The attic shows likely human activity in: "
                    + ", ".join(_room_names(attic_human, limit=3))
                    + "."
                )
            return "I do not currently see strong signs of attic occupancy."

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
                detail_bits.append(f"It is classified as {classification} with confidence {confidence_score} percent.")
                detail_bits.append(
                    f"Human likelihood is {human_likelihood} percent and automation likelihood is {automation_likelihood} percent."
                )

                return summary + " " + " ".join(detail_bits)

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

    if any(
        phrase in actual_question
        for phrase in [
            "which rooms are occupied",
            "what rooms are occupied",
            "occupancy",
            "is anyone home",
        ]
    ):
        occupied_rooms = [r for r in ranked_rooms if str(r.get("classification", "")).lower() == "occupied"]
        if occupied_rooms:
            return "The rooms that currently look occupied are: " + ", ".join(_room_names(occupied_rooms, limit=6)) + "."
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
