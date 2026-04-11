from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.pending_approval_service import get_pending_approval_service

pending_approval_bp = Blueprint("pending_approval_bp", __name__)


@pending_approval_bp.route("/ai/approvals/pending", methods=["GET"])
def approvals_pending():
    try:
        return jsonify(get_pending_approval_service().list_pending())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@pending_approval_bp.route("/ai/approvals/create", methods=["POST"])
def approvals_create():
    payload = request.get_json(silent=True) or {}

    action = payload.get("action") or {}
    auth_level = str(payload.get("auth_level") or "approval_required")
    approval_method = str(payload.get("approval_method") or "future_loxone_nfc_or_keypad")
    question = payload.get("question")
    room_id = payload.get("room_id")
    requested_by = payload.get("requested_by")
    expires_in_seconds = payload.get("expires_in_seconds")

    try:
        result = get_pending_approval_service().create_request(
            action=action,
            auth_level=auth_level,
            approval_method=approval_method,
            question=question,
            room_id=room_id,
            requested_by=requested_by,
            expires_in_seconds=expires_in_seconds,
        )
        return jsonify({
            "status": "ok",
            "approval": result,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@pending_approval_bp.route("/ai/approvals/approve", methods=["POST"])
def approvals_approve():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    approved_by = payload.get("approved_by")
    approval_source = payload.get("approval_source")

    if not token:
        return jsonify({"status": "error", "error": "Missing token"}), 400

    try:
        result = get_pending_approval_service().approve(
            token=token,
            approved_by=approved_by,
            approval_source=approval_source,
        )
        return jsonify({
            "status": "ok",
            "approval": result,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@pending_approval_bp.route("/ai/approvals/consume", methods=["POST"])
def approvals_consume():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()

    if not token:
        return jsonify({"status": "error", "error": "Missing token"}), 400

    try:
        result = get_pending_approval_service().consume(token)
        return jsonify({
            "status": "ok",
            "approval": result,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@pending_approval_bp.route("/ai/approvals/get", methods=["GET"])
def approvals_get():
    token = str(request.args.get("token") or "").strip()
    if not token:
        return jsonify({"status": "error", "error": "Missing token"}), 400

    item = get_pending_approval_service().get(token)
    if not item:
        return jsonify({"status": "error", "error": "Unknown or expired token"}), 404

    return jsonify({
        "status": "ok",
        "approval": item,
    })
