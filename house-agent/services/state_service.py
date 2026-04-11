# services/state_service.py

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock

_STATE_LOCK = RLock()

_STATE = {
    "audio": {
        "is_playing": False,
        "active_target": None,
        "active_player_id": None,
        "route_mode": None,
        "source": None,
        "started_at": None,
        "last_completed_at": None,
    },
    "relay_groups": {
        "living_speaker_module": False,
    },
    "groups": {
        "party": {
            "is_active": False,
            "last_changed_at": None,
        }
    }
}


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_state():
    with _STATE_LOCK:
        return deepcopy(_STATE)


def get_audio_state():
    with _STATE_LOCK:
        return deepcopy(_STATE["audio"])


def set_audio_state(**kwargs):
    with _STATE_LOCK:
        _STATE["audio"].update(kwargs)
        return deepcopy(_STATE["audio"])


def mark_audio_started(target, player_id, route_mode, source="system"):
    with _STATE_LOCK:
        _STATE["audio"].update({
            "is_playing": True,
            "active_target": target,
            "active_player_id": player_id,
            "route_mode": route_mode,
            "source": source,
            "started_at": _utc_now_iso(),
        })
        return deepcopy(_STATE["audio"])


def mark_audio_finished():
    with _STATE_LOCK:
        _STATE["audio"].update({
            "is_playing": False,
            "active_target": None,
            "active_player_id": None,
            "route_mode": None,
            "source": None,
            "started_at": None,
            "last_completed_at": _utc_now_iso(),
        })
        return deepcopy(_STATE["audio"])


def get_relay_groups_state():
    with _STATE_LOCK:
        return deepcopy(_STATE["relay_groups"])


def is_relay_group_enabled(group_name: str) -> bool:
    with _STATE_LOCK:
        return bool(_STATE["relay_groups"].get(group_name, False))


def set_relay_group_enabled(group_name: str, enabled: bool):
    with _STATE_LOCK:
        _STATE["relay_groups"][group_name] = bool(enabled)
        return deepcopy(_STATE["relay_groups"])


def get_group_state(group_name: str):
    with _STATE_LOCK:
        return deepcopy(_STATE["groups"].get(group_name, {
            "is_active": False,
            "last_changed_at": None,
        }))


def set_group_active(group_name: str, active: bool):
    with _STATE_LOCK:
        if group_name not in _STATE["groups"]:
            _STATE["groups"][group_name] = {}

        _STATE["groups"][group_name].update({
            "is_active": bool(active),
            "last_changed_at": _utc_now_iso(),
        })
        return deepcopy(_STATE["groups"][group_name])
