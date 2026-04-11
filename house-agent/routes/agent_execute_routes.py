from flask import Blueprint, request, jsonify
from services.agent_executor import execute_safe_action

agent_exec_bp = Blueprint("agent_exec", __name__)


@agent_exec_bp.post("/agent/execute")
def agent_execute():
    data = request.get_json(force=True)
    action = data.get("action")

    if not action:
        return jsonify({"status": "error", "error": "Missing action"}), 400

    result = execute_safe_action(action)
    return jsonify(result)
