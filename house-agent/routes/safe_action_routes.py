from flask import Blueprint, jsonify, request

from services.safe_action_service import (
    get_safe_action_inventory,
    get_safe_action,
    list_safe_actions,
    execute_safe_action,
    validate_safe_action,
    get_safe_action_runtime_state,
    get_active_safe_actions,
    get_safe_action_status_summary,
)
from services.loxone_service import fetch_loxone_state_value
from services.loxone_control_service import press_control, set_switch_control


safe_action_bp = Blueprint("safe_action_bp", __name__)


@safe_action_bp.get("/tools/safe/actions")
def safe_actions_inventory():
    return jsonify(get_safe_action_inventory())


@safe_action_bp.get("/tools/safe/actions/list")
def safe_actions_list():
    return jsonify(list_safe_actions())


@safe_action_bp.get("/tools/safe/actions/<action_name>")
def safe_action_get(action_name):
    result = get_safe_action(action_name)
    code = 200 if result.get("status") == "ok" else 404
    return jsonify(result), code


@safe_action_bp.get("/tools/safe/state")
def safe_action_state():
    return jsonify(get_safe_action_runtime_state())


@safe_action_bp.get("/tools/safe/active")
def safe_action_active():
    return jsonify(get_active_safe_actions())


@safe_action_bp.get("/tools/safe/status")
def safe_action_status():
    return jsonify(get_safe_action_status_summary())


@safe_action_bp.post("/tools/safe/execute")
def safe_action_execute():
    payload = request.get_json(silent=True) or {}
    action_name = payload.get("action_name")
    confirmed = bool(payload.get("confirmed", False))

    if not action_name:
        return jsonify({
            "status": "error",
            "message": "Missing action_name",
        }), 400

    result = execute_safe_action(action_name=action_name, confirmed=confirmed)

    code = 200
    if result.get("status") == "error":
        code = 400
    elif result.get("status") == "forbidden":
        code = 403
    elif result.get("status") == "confirmation_required":
        code = 409

    return jsonify(result), code


@safe_action_bp.post("/tools/safe/trigger")
def trigger_safe_action():
    data = request.get_json(silent=True) or {}

    control_name = data.get("control_name")
    desired_value = data.get("value", 1)

    if not control_name:
        return jsonify({
            "status": "error",
            "message": "Missing control_name"
        }), 400

    validation = validate_safe_action(control_name)
    if validation.get("status") != "ok":
        return jsonify(validation), 403

    control = validation["control"]
    ctrl_type = str(control.get("type") or "")
    room_name = str(control.get("room_name") or "")
    states = control.get("states", {}) or {}

    try:
        if ctrl_type.lower() == "switch":
            state_uuid = states.get("active")
            live_before = None
            live_after = None

            if state_uuid:
                try:
                    live_before = fetch_loxone_state_value(state_uuid)
                except Exception:
                    live_before = None

            result = set_switch_control(
                room_name=room_name,
                control_name=control_name,
                value=desired_value,
            )

            if state_uuid:
                try:
                    live_after = fetch_loxone_state_value(state_uuid)
                except Exception:
                    live_after = None

            return jsonify({
                "status": "ok",
                "mode": "switch",
                "control_name": control_name,
                "room_name": room_name,
                "requested_value": desired_value,
                "result": result,
                "live_before": live_before,
                "live_after": live_after
            })

        result = press_control(room_name=room_name, control_name=control_name)

        return jsonify({
            "status": "ok",
            "mode": "button_press",
            "control_name": control_name,
            "room_name": room_name,
            "result": result
        })

    except Exception as exc:
        return jsonify({
            "status": "error",
            "control_name": control_name,
            "room_name": room_name,
            "message": str(exc)
        }), 500
