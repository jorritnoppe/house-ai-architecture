# services/approved_action_executor_service.py
from __future__ import annotations

from typing import Any, Dict

from services.action_auth_service import classify_action_auth
from services.pending_approval_service import get_pending_approval_service
from services.approved_action_executor_service_helpers import execute_action_via_flask


def execute_approved_action(token: str) -> Dict[str, Any]:
    token = str(token or "").strip()
    if not token:
        return {
            "status": "error",
            "reason": "Missing token",
        }

    approval = get_pending_approval_service().get(token)
    if not approval:
        return {
            "status": "error",
            "reason": "Unknown or expired token",
        }

    if approval.get("status") not in {"approved", "executing"}:
        return {
            "status": "error",
            "reason": f"Token is not approved. Current status: {approval.get('status')}",
        }

    action = approval.get("action")
    if not isinstance(action, dict) or not action.get("target") or not action.get("type"):
        return {
            "status": "error",
            "reason": "Action is missing or invalid.",
        }

    auth_result = classify_action_auth(action)
    auth_level = str(auth_result.get("auth_level") or "")

    if auth_level not in {"approval_required", "safe_read"}:
        return {
            "status": "error",
            "reason": f"Action auth level is not executable after approval: {auth_level or 'unknown'}",
            "auth_result": auth_result,
        }

    return execute_action_via_flask(action)
