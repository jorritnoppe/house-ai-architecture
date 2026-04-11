from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.approved_action_executor_service import execute_approved_action
from services.pending_approval_service import get_pending_approval_service

approved_action_bp = Blueprint("approved_action_bp", __name__)


@approved_action_bp.route("/ai/approved-actions/execute", methods=["POST"])
def approved_actions_execute():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()

    if not token:
        return jsonify({"status": "error", "error": "Missing token"}), 400

    approval = get_pending_approval_service().get(token)
    if not approval:
        return jsonify({"status": "error", "error": "Unknown or expired token"}), 404

    if approval.get("status") != "approved":
        return jsonify({"status": "error", "error": "Token is not approved"}), 400

    try:
        exec_result = execute_approved_action(token)

        if exec_result.get("status") != "ok":
            return jsonify(exec_result), 400

        consume_result = get_pending_approval_service().consume(token)

        return jsonify({
            "status": "ok",
            "approval": consume_result,
            "executor_result": exec_result,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400
