from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.action_auth_service import classify_action_auth

action_auth_bp = Blueprint("action_auth_bp", __name__)


@action_auth_bp.route("/ai/auth/check", methods=["POST"])
def ai_auth_check():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action") or {}
    result = classify_action_auth(action)
    return jsonify(result)
