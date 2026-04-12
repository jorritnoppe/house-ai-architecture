from __future__ import annotations

import random
import threading
import time
import uuid
from pathlib import Path

import requests
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.stt_service import transcribe_wav
from services.agent_query_service import run_agent_query
from services.ai_safe_action_router import route_ai_safe_action
from services.voice_service import say_text




voice_input_bp = Blueprint("voice_input", __name__)

VOICE_UPLOAD_DIR = Path("/home/jnoppe/house-agent/data/voice_uploads")
VOICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".wav"}

ROOM_LOCKS: dict[str, float] = {}
ROOM_LOCKS_GUARD = threading.Lock()
ROOM_LOCK_TIMEOUT_SEC = 45

THINKING_PHRASES = [
    "Okay, I am thinking.",
    "One moment, I am checking.",
    "Let me think about that.",
    "Okay, give me a second.",
    "I am looking into that now.",
    "Alright, I am checking that.",
    "Just a moment, I am working on it.",
    "Okay, let me figure that out.",
]

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


def _run_local_agent_query(question: str, confirmed: bool = False) -> dict:
    safe_match = _looks_like_safe_action_text(question)

    if safe_match:
        safe_action_result = route_ai_safe_action(
            text=question,
            confirmed=confirmed,
        )

        if safe_action_result.get("status") != "error":
            return {
                "status": safe_action_result.get("status", "ok"),
                "question": question,
                "mode": "safe_action_router",
                "route_guard": "voice_query_last_safe_action",
                "answer": safe_action_result.get("summary", "Safe action processed."),
                "safe_action": safe_action_result,
            }

    return run_agent_query(question)




def pick_thinking_phrase() -> str:
    return random.choice(THINKING_PHRASES)


def acquire_room_lock(room_id: str) -> bool:
    now = time.time()
    room_key = (room_id or "default").strip() or "default"

    with ROOM_LOCKS_GUARD:
        expires_at = ROOM_LOCKS.get(room_key)
        if expires_at and expires_at > now:
            return False

        ROOM_LOCKS[room_key] = now + ROOM_LOCK_TIMEOUT_SEC
        return True


def refresh_room_lock(room_id: str) -> None:
    now = time.time()
    room_key = (room_id or "default").strip() or "default"

    with ROOM_LOCKS_GUARD:
        if room_key in ROOM_LOCKS:
            ROOM_LOCKS[room_key] = now + ROOM_LOCK_TIMEOUT_SEC


def release_room_lock(room_id: str) -> None:
    room_key = (room_id or "default").strip() or "default"

    with ROOM_LOCKS_GUARD:
        ROOM_LOCKS.pop(room_key, None)


def _latest_file_for_room(room_id: str) -> Path | None:
    room_dir = VOICE_UPLOAD_DIR / room_id
    if not room_dir.exists():
        return None

    files = [
        p for p in room_dir.glob("*.wav")
        if "_mono16k" not in p.name
    ]
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _safe_voice_say(text: str, player: str, timeout: int = 30) -> dict:
    try:
        result = say_text(text, player_id=player)
        return {
            "status": "ok",
            "player_id": result.get("player_id"),
            "volume": result.get("volume"),
            "audio_url": result.get("audio_url"),
            "audio_file": result.get("audio_file"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



@voice_input_bp.route("/voice/upload", methods=["POST"])
def voice_upload():
    if "file" not in request.files:
        return jsonify({"status": "error", "error": "missing file"}), 400

    file = request.files["file"]
    room_id = request.form.get("room_id", "unknown").strip() or "unknown"
    source_id = request.form.get("source_id", "unknown").strip() or "unknown"

    if not file.filename:
        return jsonify({"status": "error", "error": "empty filename"}), 400

    safe_name = secure_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"status": "error", "error": f"unsupported file type: {ext}"}), 400

    room_dir = VOICE_UPLOAD_DIR / room_id
    room_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    target = room_dir / f"{file_id}.wav"
    file.save(target)

    latest_link = room_dir / "latest.wav"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(target.name)

    return jsonify({
        "status": "ok",
        "room_id": room_id,
        "source_id": source_id,
        "saved_as": str(target),
        "latest": str(latest_link),
        "size_bytes": target.stat().st_size,
    })


@voice_input_bp.route("/voice/input/status", methods=["GET"])
def voice_input_status():
    room_id = request.args.get("room_id", "office")
    latest = _latest_file_for_room(room_id)
    return jsonify({
        "status": "ok",
        "room_id": room_id,
        "upload_dir": str(VOICE_UPLOAD_DIR / room_id),
        "latest_file": str(latest) if latest else None,
        "latest_exists": bool(latest),
    })


@voice_input_bp.route("/voice/process-last", methods=["POST"])
def voice_process_last():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id", "office")
    player = payload.get("player", "desk")

    latest = _latest_file_for_room(room_id)
    if not latest:
        return jsonify({"status": "error", "error": f"no uploaded audio found for room {room_id}"}), 404

    say_response = _safe_voice_say(
        text=f"I received your microphone test from {room_id}.",
        player=player,
        timeout=120,
    )

    return jsonify({
        "status": "ok",
        "room_id": room_id,
        "player": player,
        "latest_file": str(latest),
        "voice_say_response": say_response,
    })


@voice_input_bp.route("/voice/transcribe-last", methods=["POST"])
def voice_transcribe_last():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id", "office")
    language = payload.get("language", "en")

    latest = _latest_file_for_room(room_id)
    if not latest:
        return jsonify({"status": "error", "error": f"no uploaded audio found for room {room_id}"}), 404

    result = transcribe_wav(str(latest), language=language)

    return jsonify({
        "status": "ok",
        "room_id": room_id,
        "latest_file": str(latest),
        "transcript": result["text"],
        "language": result["language"],
        "language_probability": result["language_probability"],
        "mono_file": result["mono_file"],
    })


@voice_input_bp.route("/voice/query-last", methods=["POST"])
def voice_query_last():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id", "office")
    player = payload.get("player", "desk")
    language = payload.get("language", "en")

    if not acquire_room_lock(room_id):
        busy_text = "I am already handling another request in this room."
        busy_say_data = _safe_voice_say(busy_text, player, timeout=30)

        return jsonify({
            "status": "busy",
            "room_id": room_id,
            "player": player,
            "answer": busy_text,
            "voice_say_response": busy_say_data,
        }), 429

    try:
        latest = _latest_file_for_room(room_id)
        if not latest:
            return jsonify({
                "status": "error",
                "error": f"no uploaded audio found for room {room_id}",
            }), 404

        refresh_room_lock(room_id)

        stt_result = transcribe_wav(str(latest), language=language)
        transcript = stt_result["text"].strip()

        if not transcript:
            return jsonify({
                "status": "error",
                "error": "empty transcript",
                "room_id": room_id,
                "latest_file": str(latest),
            }), 400

        refresh_room_lock(room_id)

        processing_done = {"done": False}
        thinking_spoken = {"done": False}

        def delayed_thinking():
            time.sleep(2.0)
            if processing_done["done"] or thinking_spoken["done"]:
                return
            try:
                requests.post(
                    "http://127.0.0.1:8000/voice/say",
                    json={"text": pick_thinking_phrase(), "player": player},
                    timeout=30,
                )
                thinking_spoken["done"] = True
            except Exception:
                pass

        thinking_thread = threading.Thread(target=delayed_thinking, daemon=True)
        thinking_thread.start()


        confirmed = bool(payload.get("confirmed", False))
        agent_data = _run_local_agent_query(
            question=transcript,
            confirmed=confirmed,
        )
        answer = agent_data.get("answer", "I could not generate an answer.")


        answer = agent_data.get("answer", "I could not generate an answer.")

        processing_done["done"] = True
        thinking_spoken["done"] = True
        refresh_room_lock(room_id)

        say_data = _safe_voice_say(answer, player, timeout=180)

        return jsonify({
            "status": "ok",
            "room_id": room_id,
            "player": player,
            "latest_file": str(latest),
            "transcript": transcript,
            "answer": answer,
            "voice_say_response": say_data,
        })

    finally:
        release_room_lock(room_id)
