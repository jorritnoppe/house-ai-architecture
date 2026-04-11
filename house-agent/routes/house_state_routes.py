from __future__ import annotations

from flask import Blueprint, jsonify

from services.house_state_service import get_house_state

house_state_bp = Blueprint("house_state_bp", __name__)


@house_state_bp.route("/ai/house_state", methods=["GET"])
def ai_house_state():
    try:
        return jsonify(get_house_state())
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500
