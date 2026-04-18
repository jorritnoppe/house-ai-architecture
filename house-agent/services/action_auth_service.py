from __future__ import annotations

from typing import Any, Dict

SAFE_READ_TARGETS = {
    "/ai/house_state",
    "/ai/playback_state",
    "/ai/power_now",
    "/ai/energy_summary",
    "/ai/energy_today",
    "/ai/nodes/health",
    "/ai/nodes/overview",
    "/ai/nodes/capabilities",
    "/ai/service/health",
    "/ai/services/overview",
    "/ai/service/summary",
    "/ai/node/summary",
    "/ai/node/alerts",
    "/ai/loxone_history_presence_ai",
    "/ai/loxone_history_binary_active",
    "/ai/loxone_history_binary_changes",
    "/ai/loxone_history_telemetry_latest",
    "/ai/loxone_history_room_activity_ai",
    "/ai/loxone_history_last_change",
    "/ai/sma_summary",
    "/ai/electricity_price_now",
    "/ai/cheapest_hours_today",
    "/ai/salt_tank_level",
    "/ai/water_temperatures",
    "/ai/water_softener_overview",
    "/ai/pdata_gas_summary",
    "/ai/pdata_full_overview",
    "/ai/unified_energy_summary",
    "/ai/unified_energy_snapshot",
    "/tools/music/play_ai_house",
    "/tools/music/stop_room",
}


APPROVAL_REQUIRED_TARGETS = {
    "/tools/audio/announce",
    "/tools/audio/node_power/on",
    "/tools/audio/node_power/off",
    "/tools/music/control",
    "/tools/relay/set",
    "/tools/loxone/control",
    "/api/trade/execute-approved",
}

BLOCKED_TARGET_PREFIXES = {
    "/admin/",
    "/debug/",
    "/unsafe/",
}


def classify_action_auth(action: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(action, dict):
        return {
            "status": "error",
            "allowed": False,
            "auth_level": "invalid",
            "reason": "Action is missing or invalid.",
            "approval_method": None,
        }

    action_type = str(action.get("type") or "").strip().lower()
    target = str(action.get("target") or "").strip()

    if not action_type or not target:
        return {
            "status": "error",
            "allowed": False,
            "auth_level": "invalid",
            "reason": "Action type or target is missing.",
            "approval_method": None,
        }

    for prefix in BLOCKED_TARGET_PREFIXES:
        if target.startswith(prefix):
            return {
                "status": "ok",
                "allowed": False,
                "auth_level": "blocked",
                "reason": f"Target {target} is blocked by policy.",
                "approval_method": None,
            }

    if target in SAFE_READ_TARGETS:
        return {
            "status": "ok",
            "allowed": True,
            "auth_level": "safe_read",
            "reason": f"Target {target} is classified as read-only safe access.",
            "approval_method": None,
        }

    if target in APPROVAL_REQUIRED_TARGETS:
        return {
            "status": "ok",
            "allowed": False,
            "auth_level": "approval_required",
            "reason": f"Target {target} requires approval before execution.",
            "approval_method": "future_loxone_nfc_or_keypad",
        }

    if action_type == "route" and target.startswith("/ai/"):
        return {
            "status": "ok",
            "allowed": True,
            "auth_level": "safe_read",
            "reason": f"Internal AI route {target} is allowed by default safe-read policy.",
            "approval_method": None,
        }

    return {
        "status": "ok",
        "allowed": False,
        "auth_level": "unknown",
        "reason": f"Target {target} is not yet classified in the authorization policy.",
        "approval_method": None,
    }


def check_action_auth(action: Dict[str, Any] | None) -> Dict[str, Any]:
    return classify_action_auth(action)


def is_action_allowed_now(action: Dict[str, Any] | None) -> bool:
    result = classify_action_auth(action)
    return bool(result.get("allowed") is True)


def explain_action_auth(action: Dict[str, Any] | None) -> str:
    result = classify_action_auth(action)

    auth_level = result.get("auth_level", "unknown")
    reason = result.get("reason", "No reason available.")
    approval_method = result.get("approval_method")

    if approval_method:
        return f"{auth_level}: {reason} Approval method: {approval_method}."
    return f"{auth_level}: {reason}"
