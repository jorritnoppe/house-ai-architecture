from __future__ import annotations

from typing import Any, Dict

from extensions import app


def execute_action_via_flask(action: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(action, dict):
        return {
            "status": "error",
            "reason": "Action must be a dict",
        }

    action_type = str(action.get("type") or "").strip().lower()
    target = str(action.get("target") or "").strip()
    params = action.get("params") or {}
    method = str(action.get("method") or "").strip().upper()

    if not isinstance(params, dict):
        params = {}

    if action_type != "route":
        return {
            "status": "error",
            "reason": f"Unsupported action type: {action_type or 'unknown'}",
            "action": action,
        }

    if not target.startswith("/"):
        return {
            "status": "error",
            "reason": f"Invalid route target: {target!r}",
            "action": action,
        }

    if not method:
        if target.startswith("/tools/"):
            method = "POST"
        else:
            method = "GET"

    try:
        with app.app_context():
            with app.test_client() as client:
                if method == "POST":
                    response = client.post(target, json=params)
                elif method == "GET":
                    response = client.get(target, query_string=params)
                else:
                    return {
                        "status": "error",
                        "reason": f"Unsupported route method: {method}",
                        "target": target,
                        "action_type": action_type,
                        "params": params,
                    }

                try:
                    data = response.get_json(silent=True)
                except Exception:
                    data = None

                return {
                    "status": "ok" if response.status_code < 400 else "error",
                    "http_status": response.status_code,
                    "target": target,
                    "action_type": action_type,
                    "method": method,
                    "params": params,
                    "data": data,
                    "raw_text": response.get_data(as_text=True),
                }

    except Exception as exc:
        app.logger.exception("Approved action execution failed for target=%s", target)
        return {
            "status": "error",
            "reason": str(exc),
            "target": target,
            "action_type": action_type,
            "method": method,
            "params": params,
        }
