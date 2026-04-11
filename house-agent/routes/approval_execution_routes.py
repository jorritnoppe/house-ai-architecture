from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.approved_action_executor_service import execute_approved_action
from services.pending_approval_service import get_pending_approval_service

approval_execution_bp = Blueprint("approval_execution_bp", __name__)


def _find_latest_pending(items: list[dict], target: str | None = None) -> dict | None:
    pending = [item for item in items if item.get("status") == "pending" and not item.get("consumed")]

    if target:
        pending = [
            item for item in pending
            if str((item.get("action") or {}).get("target") or "").strip() == target
        ]

    if not pending:
        return None

    pending.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return pending[0]


@approval_execution_bp.route("/ai/approvals/approve-and-execute-latest", methods=["POST"])
def approve_and_execute_latest():
    payload = request.get_json(silent=True) or {}

    approval_source = str(payload.get("approval_source") or "loxone_manual").strip()
    approved_by = str(payload.get("approved_by") or approval_source).strip()
    target_filter = str(payload.get("target") or "").strip() or None

    service = get_pending_approval_service()
    pending_data = service.list_pending()
    items = pending_data.get("items", []) or []

    latest = _find_latest_pending(items, target=target_filter)
    if not latest:
        return jsonify({
            "status": "error",
            "error": "No pending approval found",
        }), 404

    token = str(latest.get("token") or "").strip()
    if not token:
        return jsonify({
            "status": "error",
            "error": "Pending approval has no token",
        }), 400

    try:
        approved = service.approve(
            token=token,
            approved_by=approved_by,
            approval_source=approval_source,
        )

        executor_result = execute_approved_action(token)
        if executor_result.get("status") == "ok":
            consumed = service.consume(token)
        else:
            consumed = approved

        return jsonify({
            "status": "ok" if executor_result.get("status") == "ok" else "error",
            "approval": consumed,
            "executor_result": executor_result,
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 400


@approval_execution_bp.route("/ai/approvals/approve-and-execute-token", methods=["POST"])
def approve_and_execute_token():
    payload = request.get_json(silent=True) or {}

    token = str(payload.get("token") or "").strip()
    approval_source = str(payload.get("approval_source") or "loxone_manual").strip()
    approved_by = str(payload.get("approved_by") or approval_source).strip()

    if not token:
        return jsonify({
            "status": "error",
            "error": "Missing token",
        }), 400

    service = get_pending_approval_service()

    try:
        approved = service.approve(
            token=token,
            approved_by=approved_by,
            approval_source=approval_source,
        )

        executor_result = execute_approved_action(token)
        if executor_result.get("status") == "ok":
            consumed = service.consume(token)
        else:
            consumed = approved

        return jsonify({
            "status": "ok" if executor_result.get("status") == "ok" else "error",
            "approval": consumed,
            "executor_result": executor_result,
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 400
