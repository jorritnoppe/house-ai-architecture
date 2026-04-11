from flask import Blueprint, jsonify, request

from services.audio_orchestrator import announce, stop, group_on, group_off
from services.state_service import get_state

audio_bp = Blueprint("audio_bp", __name__)


from flask import Blueprint, jsonify, request

from services.audio_orchestrator import announce, stop, group_on, group_off
from services.state_service import get_state

audio_bp = Blueprint("audio_bp", __name__)


@audio_bp.post("/tools/audio/announce")
def audio_announce():
    try:
        body = request.get_json(silent=True) or {}
        text = body.get("text", "")
        target = body.get("target", "living")
        priority = body.get("priority", "normal")
        source = body.get("source", "api")
        level = body.get("level")
        volume = body.get("volume")

        result = announce(
            text=text,
            target=target,
            priority=priority,
            source=source,
            level=level,
            volume=volume,
        )
        status_code = 200 if result.get("status") in {"ok", "busy"} else 400
        return jsonify(result), status_code

    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 400


@audio_bp.post("/tools/audio/stop")
def audio_stop():
    try:
        body = request.get_json(silent=True) or {}
        target = body.get("target")
        result = stop(target=target)
        status_code = 200 if result.get("status") == "ok" else 400
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 400


@audio_bp.post("/tools/audio/group/on")
def audio_group_on():
    try:
        body = request.get_json(silent=True) or {}
        target = body.get("target", "")
        source = body.get("source", "api")

        result = group_on(target=target, source=source)
        status_code = 200 if result.get("status") == "ok" else 400
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 400


@audio_bp.post("/tools/audio/group/off")
def audio_group_off():
    try:
        body = request.get_json(silent=True) or {}
        target = body.get("target", "")
        source = body.get("source", "api")

        result = group_off(target=target, source=source)
        status_code = 200 if result.get("status") == "ok" else 400
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 400


@audio_bp.get("/tools/audio/state")
def audio_state():
    return jsonify({
        "status": "ok",
        "state": get_state(),
    }), 200
