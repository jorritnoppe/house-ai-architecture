# services/audio_orchestrator.py

import logging
import threading
import time

from services.device_registry import get_audio_target_config
from services.event_service import publish_event
from services.state_service import (
    get_audio_state,
    get_group_state,
    is_relay_group_enabled,
    mark_audio_finished,
    mark_audio_started,
    set_group_active,
    set_relay_group_enabled,
)
from services.voice_service import stop_player as voice_stop_player
from services.voice_service import say_text as voice_say_text
from services.announcement_service import announce_text as styled_announce_text
from services.loxone_action_service import audio_speaker_route

logger = logging.getLogger(__name__)

_AUDIO_LOCK = threading.RLock()


def _stop_player(player_id: str):
    return voice_stop_player(player_id)


def _speak_text(player_id: str, text: str, level: str | None = None, volume=None):
    normalized_level = (level or "").strip().lower()

    # normal/plain = regular TTS path
    if normalized_level in {"", "plain", "normal"}:
        return voice_say_text(
            text=text,
            player_id=player_id,
            volume=volume,
        )

    # attention/warning/emergency/etc = announcement path
    return styled_announce_text(
        text=text,
        level=normalized_level,
        player_id=player_id,
        volume=volume,
        manage_speaker_route=False,
    )

def _prepare_relay_group(config: dict):
    if not config.get("requires_audio_relay"):
        return None

    relay_group = config.get("audio_relay_group")
    if not relay_group:
        return None

    if is_relay_group_enabled(relay_group):
        event = {
            "relay_group": relay_group,
            "target": config["target_key"],
            "status": "already_enabled",
        }
        publish_event("audio.relay.already_enabled", event)
        return event

    relay_target = config.get("speaker_route_target") or config["target_key"]

    publish_event("audio.relay.enable.requested", {
        "relay_group": relay_group,
        "target": config["target_key"],
        "relay_target": relay_target,
    })

    result = audio_speaker_route(relay_target, "on")
    set_relay_group_enabled(relay_group, True)

    warmup = float(config.get("warmup_seconds", 0.0))
    if warmup > 0:
        time.sleep(warmup)

    payload = {
        "relay_group": relay_group,
        "target": config["target_key"],
        "relay_target": relay_target,
        "result": result,
    }

    publish_event("audio.relay.enabled", payload)
    return payload


def _release_relay_group(config: dict):
    if not config.get("requires_audio_relay"):
        return None

    if not config.get("release_after_play", False):
        return None

    relay_group = config.get("audio_relay_group")
    if not relay_group:
        return None

    if not is_relay_group_enabled(relay_group):
        event = {
            "relay_group": relay_group,
            "target": config["target_key"],
            "status": "already_disabled",
        }
        publish_event("audio.relay.already_disabled", event)
        return event

    delay_seconds = float(config.get("release_delay_seconds", 0.0))
    if delay_seconds > 0:
        time.sleep(delay_seconds)

    relay_target = config.get("speaker_route_target") or config["target_key"]

    publish_event("audio.relay.disable.requested", {
        "relay_group": relay_group,
        "target": config["target_key"],
        "relay_target": relay_target,
    })

    result = audio_speaker_route(relay_target, "off")
    set_relay_group_enabled(relay_group, False)

    payload = {
        "relay_group": relay_group,
        "target": config["target_key"],
        "relay_target": relay_target,
        "result": result,
    }

    publish_event("audio.relay.disabled", payload)
    return payload


def announce(
    text: str,
    target: str = "living",
    priority: str = "normal",
    source: str = "system",
    level: str | None = None,
    volume=None,
    prepare_result = None,
    release_result = None,
):
    if not text or not str(text).strip():
        return {"status": "error", "error": "Text is empty"}

    config = get_audio_target_config(target)

    if config.get("target_type") != "player":
        return {
            "status": "error",
            "error": f"Target '{config['target_key']}' is not a direct playback target",
            "target": config["target_key"],
            "target_type": config.get("target_type"),
        }

    with _AUDIO_LOCK:
        current = get_audio_state()
        if current.get("is_playing"):
            return {
                "status": "busy",
                "error": "Audio already playing",
                "current_audio_state": current,
            }

        publish_event("audio.playback.requested", {
            "target": config["target_key"],
            "player_id": config["player_id"],
            "priority": priority,
            "source": source,
            "route_mode": config.get("route_mode"),
            "level": level,
            "volume": volume,
        })

        try:
            prepare_result = _prepare_relay_group(config)

            if config.get("stop_before_play"):
                _stop_player(config["player_id"])

            mark_audio_started(
                target=config["target_key"],
                player_id=config["player_id"],
                route_mode=config.get("route_mode"),
                source=source,
            )

            publish_event("audio.playback.started", {
                "target": config["target_key"],
                "player_id": config["player_id"],
                "route_mode": config.get("route_mode"),
                "level": level,
            })

            speak_result = _speak_text(
                player_id=config["player_id"],
                text=text,
                level=level,
                volume=volume,
            )

            publish_event("audio.playback.finished", {
                "target": config["target_key"],
                "player_id": config["player_id"],
                "speak_result": speak_result,
            })

            return {
                "status": "ok",
                "target": config["target_key"],
                "player_id": config["player_id"],
                "route_mode": config.get("route_mode"),
                "spoken": text,
                "priority": priority,
                "source": source,
                "level": level,
                "volume": volume,
                "result": speak_result,
                "prepare_result": prepare_result,
                "release_result": release_result,
            }

        except Exception as exc:
            logger.exception("Audio announce failed")
            publish_event("audio.playback.failed", {
                "target": config["target_key"],
                "error": str(exc),
            })
            return {
                "status": "error",
                "error": str(exc),
                "target": config["target_key"],
            }

        finally:
            try:
                release_result = _release_relay_group(config)
            finally:
                mark_audio_finished()


def stop(target: str | None = None):
    with _AUDIO_LOCK:
        if target:
            config = get_audio_target_config(target)

            if config.get("target_type") != "player":
                return {
                    "status": "error",
                    "error": f"Target '{config['target_key']}' is not a direct playback target",
                    "target": config["target_key"],
                }

            result = _stop_player(config["player_id"])
            publish_event("audio.stop.requested", {
                "target": config["target_key"],
                "player_id": config["player_id"],
            })
            mark_audio_finished()

            return {
                "status": "ok",
                "target": config["target_key"],
                "player_id": config["player_id"],
                "result": result,
            }

        state = get_audio_state()
        player_id = state.get("active_player_id")
        if not player_id:
            return {"status": "ok", "message": "No active playback"}

        result = _stop_player(player_id)
        publish_event("audio.stop.requested", {
            "target": state.get("active_target"),
            "player_id": player_id,
        })
        mark_audio_finished()

        return {
            "status": "ok",
            "target": state.get("active_target"),
            "player_id": player_id,
            "result": result,
        }


def group_on(target: str, source: str = "system"):
    config = get_audio_target_config(target)

    if config.get("target_type") != "group":
        return {
            "status": "error",
            "error": f"Target '{config['target_key']}' is not a group target",
            "target": config["target_key"],
        }

    current = get_group_state(config["target_key"])
    if current.get("is_active"):
        return {
            "status": "ok",
            "target": config["target_key"],
            "message": "Group already active",
        }

    publish_event("audio.group.on.requested", {
        "target": config["target_key"],
        "source": source,
        "endpoint": config.get("on_endpoint"),
    })

    # For now keep this as an API-style response object.
    # Later this can call a real service function directly if desired.
    result = {
        "status": "ok",
        "endpoint": config.get("on_endpoint"),
    }

    set_group_active(config["target_key"], True)

    publish_event("audio.group.on.completed", {
        "target": config["target_key"],
        "result": result,
    })

    return {
        "status": "ok",
        "target": config["target_key"],
        "group_mode": config.get("group_mode"),
        "result": result,
    }


def group_off(target: str, source: str = "system"):
    config = get_audio_target_config(target)

    if config.get("target_type") != "group":
        return {
            "status": "error",
            "error": f"Target '{config['target_key']}' is not a group target",
            "target": config["target_key"],
        }

    current = get_group_state(config["target_key"])
    if not current.get("is_active"):
        return {
            "status": "ok",
            "target": config["target_key"],
            "message": "Group already inactive",
        }

    publish_event("audio.group.off.requested", {
        "target": config["target_key"],
        "source": source,
        "endpoint": config.get("off_endpoint"),
    })

    result = {
        "status": "ok",
        "endpoint": config.get("off_endpoint"),
    }

    set_group_active(config["target_key"], False)

    publish_event("audio.group.off.completed", {
        "target": config["target_key"],
        "result": result,
    })

    return {
        "status": "ok",
        "target": config["target_key"],
        "group_mode": config.get("group_mode"),
        "result": result,
    }
