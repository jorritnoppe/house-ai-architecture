from __future__ import annotations

from flask import Blueprint, jsonify

from services.unified_playback_state_service import get_unified_playback_state

playback_state_bp = Blueprint("playback_state_bp", __name__)


@playback_state_bp.route("/ai/playback_state", methods=["GET"])
def ai_playback_state():
    try:
        return jsonify(get_unified_playback_state(cooldown_seconds=2))
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500
