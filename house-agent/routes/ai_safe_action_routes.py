from flask import Blueprint, jsonify, request

from services.ai_safe_action_router import route_ai_safe_action


ai_safe_action_bp = Blueprint("ai_safe_action_bp", __name__)


@ai_safe_action_bp.post("/agent/safe_action")
def agent_safe_action():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()
    confirmed = bool(payload.get("confirmed", False))

    if not text:
        return jsonify({
            "status": "no_match",
            "message": "No safe action matched.",
            "input_text": text,
        }), 400

    result = route_ai_safe_action(text=text, confirmed=confirmed)

    code = 200
    if result.get("status") == "error":
        code = 400
    elif result.get("status") == "forbidden":
        code = 403
    elif result.get("status") == "confirmation_required":
        code = 409
    elif result.get("status") == "review_required":
        code = 409

    return jsonify(result), code
