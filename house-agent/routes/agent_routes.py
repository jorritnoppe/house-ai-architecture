from flask import Blueprint, jsonify, request

from extensions import app, query_api
from services.voice_service import say_text
from services.announcement_service import announce_text
from services.agent_query_service import run_agent_query
from services.ai_safe_action_router import route_ai_safe_action
import os
import requests


ELECTRICPI_LOXONE_BRIDGE_URL = os.getenv(
    "ELECTRICPI_LOXONE_BRIDGE_URL",
    "http://192.168.1.15:8877"
).rstrip("/")


agent_bp = Blueprint("agent", __name__)


def _normalize_safe_text(text: str) -> str:
    text = str(text or "").strip().lower()
    text = text.replace("_", " ")
    return " ".join(text.split())


def _has_words(text: str, words: list[str]) -> bool:
    return all(word in text for word in words)


def _looks_like_safe_action_text(text: str) -> bool:
    t = _normalize_safe_text(text)

    # Hard guard: room/floor/zone intelligence questions must never go to the
    # safe action router. These belong in the house intelligence path.
    room_intel_phrases = [
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
        "which rooms are occupied",
        "what rooms are occupied",
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
        "what is happening in",
        "what's happening in",
        "what is active in",
        "what sensors are active in",
        "give me the current state of",
        "current state of",
        "why is ",
        "which room is most active",
        "what room is most active",
        "most active room",
        "most important active room",
        "which rooms are likely being used",
        "what rooms are likely being used",
        "likely human active rooms",
        "likely occupied rooms",
        "rooms likely in use",
        "which rooms are likely automation noise",
        "which rooms were recently used by a person",
        "what rooms were recently used by a person",
        "recently used by a person",
        "recent human activity",
        "which rooms had recent human activity",
        "what rooms had recent human activity",
        "which rooms are probably being used",
        "what rooms are probably being used",
        "which rooms are probably just background automation",
        "what rooms are probably just background automation",
        "background automation",
        "background activity",
        "automation noise",
        "which rooms look like automation",
        "what rooms look like automation",
    ]

    if any(phrase in t for phrase in room_intel_phrases):
        return False

    music_words = [
        "music",
        "audio",
        "party mode",
        "party music",
        "speaker",
        "speakers",
        "playback",
        "playlist",
        "song",
        "scene",
    ]

    room_words = [
        "living room",
        "livingroom",
        "bathroom",
        "bath",
        "toilet",
        "wc",
        "wcroom",
        "badkamer",
        "woonkamer",
        "downstairs",
        "upstairs",
        "attic",
    ]

    status_phrases = [
        "what music is playing",
        "what is playing",
        "is music playing",
        "is living room music on",
        "is bathroom music on",
        "is toilet music on",
        "is party mode on",
        "status of music",
        "active actions",
        "which safe actions are active",
        "which actions are active",
        "what audio is active",
        "what music is active",
        "what playback is active",
    ]

    direct_action_phrases = [
        "start",
        "stop",
        "play",
        "enable",
        "disable",
        "switch on",
        "switch off",
    ]

    has_status = any(phrase in t for phrase in status_phrases)
    has_music = any(word in t for word in music_words)
    has_room = any(word in t for word in room_words)

    has_direct_action = any(phrase in t for phrase in direct_action_phrases)

    has_split_action = (
        _has_words(t, ["turn", "on"])
        or _has_words(t, ["turn", "off"])
        or _has_words(t, ["put", "on"])
        or _has_words(t, ["put", "off"])
    )

    # Generic room-state questions should not be routed to safe actions unless
    # they clearly mention audio/music.
    if "what is active" in t and not has_music:
        return False
    if "what is running" in t and not has_music:
        return False
    if "why is" in t and "active" in t and not has_music:
        return False
    if "what is happening" in t and not has_music:
        return False
    if "current state" in t and not has_music:
        return False

    return has_status or ((has_direct_action or has_split_action) and (has_music or has_room))



@agent_bp.post("/agent/query")
def agent_query():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question") or "").strip()
    speak = bool(payload.get("speak", False))
    player_id = str(payload.get("player_id") or "").strip()
    volume = payload.get("volume")
    confirmed = bool(payload.get("confirmed", False))

    if not question:
        return jsonify({
            "status": "error",
            "message": "missing 'question'",
        }), 400

    safe_match = _looks_like_safe_action_text(question)
    app.logger.warning(
        "AGENT_QUERY_DEBUG question=%r safe_match=%s confirmed=%s",
        question,
        safe_match,
        confirmed,
    )

    if safe_match:
        safe_action_result = route_ai_safe_action(
            text=question,
            confirmed=confirmed,
        )

        app.logger.warning(
            "AGENT_QUERY_DEBUG safe_action_result=%s",
            safe_action_result,
        )

        if safe_action_result.get("status") != "error":
            result = {
                "status": safe_action_result.get("status", "ok"),
                "question": question,
                "mode": "safe_action_router",
                "route_guard": "agent_query_safe_action_debug",
                "answer": safe_action_result.get("summary", "Safe action processed."),
                "safe_action": safe_action_result,
            }

            if speak and result.get("answer"):
                try:
                    voice_result = say_text(
                        result["answer"],
                        player_id=player_id,
                        volume=volume,
                    )
                    result["voice"] = {
                        "status": "ok",
                        "player_id": voice_result["player_id"],
                        "volume": voice_result["volume"],
                        "audio_url": voice_result["audio_url"],
                        "audio_file": voice_result["audio_file"],
                    }
                except Exception as e:
                    app.logger.exception("Voice playback failed: %s", e)
                    result["voice"] = {
                        "status": "error",
                        "message": str(e),
                    }

            return jsonify(result)

    app.logger.warning("AGENT_QUERY_DEBUG fallback_to_run_agent_query question=%r", question)
    result = run_agent_query(question)

    app.logger.warning("AGENT_QUERY_DEBUG fallback_to_run_agent_query question=%r", question)
    result = run_agent_query(question)

    debug = bool(payload.get("debug", False))

    if not debug and isinstance(result, dict):
        compact = {
            "status": result.get("status", "ok"),
            "question": question,
            "mode": result.get("mode"),
            "answer": result.get("answer"),
        }

        if "intents" in result:
            compact["intents"] = result.get("intents")

        if "auth_result" in result:
            compact["auth_result"] = {
                "status": result.get("auth_result", {}).get("status"),
                "allowed": result.get("auth_result", {}).get("allowed"),
                "auth_level": result.get("auth_result", {}).get("auth_level"),
                "approval_method": result.get("auth_result", {}).get("approval_method"),
            }

        return jsonify(compact)

    return jsonify(result)




def _speak_via_electricpi(speaker: str, text: str, owner: str = "ai", volume=None):
    text = (text or "").strip()
    if not text:
        raise ValueError("missing 'text'")

    payload = {
        "owner": owner,
        "text": text,
    }

    if volume is not None:
        payload["volume"] = volume

    response = requests.post(
        f"{ELECTRICPI_LOXONE_BRIDGE_URL}/speaker/{speaker}/speak",
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


@agent_bp.post("/house/speak/living")
def house_speak_living():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    owner = (payload.get("owner") or "ai").strip()
    volume = payload.get("volume")

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    try:
        result = _speak_via_electricpi(
            speaker="living",
            text=text,
            owner=owner,
            volume=volume,
        )
        return jsonify({
            "status": "ok",
            "speaker": "living",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@agent_bp.post("/house/speak/wc")
def house_speak_wc():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    owner = (payload.get("owner") or "ai").strip()
    volume = payload.get("volume")

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    try:
        result = _speak_via_electricpi(
            speaker="wc",
            text=text,
            owner=owner,
            volume=volume,
        )
        return jsonify({
            "status": "ok",
            "speaker": "wc",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
