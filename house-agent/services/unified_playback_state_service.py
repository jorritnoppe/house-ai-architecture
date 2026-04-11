from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from flask import current_app

from services.state_service import get_audio_state


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _get_conversation_playback_state() -> Dict[str, Any]:
    manager = current_app.config.get("conversation_manager")
    if manager is None:
        return {
            "active": False,
            "session_id": None,
            "target_room": None,
            "target_player": None,
            "started_at": None,
            "expected_end_at": None,
            "last_text": None,
        }

    try:
        return manager.get_playback_state()
    except Exception:
        return {
            "active": False,
            "session_id": None,
            "target_room": None,
            "target_player": None,
            "started_at": None,
            "expected_end_at": None,
            "last_text": None,
        }


def get_unified_playback_state(cooldown_seconds: int = 2) -> Dict[str, Any]:
    audio_state = get_audio_state()
    convo_state = _get_conversation_playback_state()

    audio_playing = bool(audio_state.get("is_playing"))
    conversation_active = bool(convo_state.get("active"))

    active = audio_playing or conversation_active

    effective_target_player = (
        convo_state.get("target_player")
        or audio_state.get("active_player_id")
    )

    effective_target_room = (
        convo_state.get("target_room")
        or audio_state.get("active_target")
    )

    source = audio_state.get("source") or ("conversation_manager" if conversation_active else None)
    route_mode = audio_state.get("route_mode")

    expected_end_at = convo_state.get("expected_end_at")
    expected_end_dt = _parse_iso(expected_end_at)
    cooldown_until = None

    if not active:
        last_completed_at = _parse_iso(audio_state.get("last_completed_at"))
        if last_completed_at:
            cooldown_until = (last_completed_at + timedelta(seconds=cooldown_seconds)).isoformat()

    in_cooldown = False
    if cooldown_until:
        cooldown_dt = _parse_iso(cooldown_until)
        if cooldown_dt and cooldown_dt > _utc_now():
            in_cooldown = True

    suppress_wake = False
    suppress_transcription = False
    suppress_reason = None

    if active:
        suppress_wake = True
        suppress_transcription = True
        suppress_reason = "active_playback"
    elif in_cooldown:
        suppress_wake = True
        suppress_transcription = False
        suppress_reason = "post_playback_cooldown"

    return {
        "status": "ok",
        "generated_at": _utc_now_iso(),
        "audio_state": deepcopy(audio_state),
        "conversation_state": deepcopy(convo_state),
        "effective": {
            "active": active,
            "audio_playing": audio_playing,
            "conversation_active": conversation_active,
            "effective_target_room": effective_target_room,
            "effective_target_player": effective_target_player,
            "source": source,
            "route_mode": route_mode,
            "expected_end_at": expected_end_at if expected_end_dt else None,
            "cooldown_until": cooldown_until,
            "suppress_wake": suppress_wake,
            "suppress_transcription": suppress_transcription,
            "suppress_reason": suppress_reason,
        },
    }
