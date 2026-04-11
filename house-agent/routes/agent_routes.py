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
    "http://audio-node.local:8877"
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

    music_words = [
        "music",
        "audio",
        "party mode",
        "party music",
        "party",
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
        "what is active",
        "what is running",
        "active actions",
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
    return jsonify(result)


def _speak_via_audio-node-1(speaker: str, text: str, owner: str = "ai", volume=None):
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
        result = _speak_via_audio-node-1(
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
        result = _speak_via_audio-node-1(
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
