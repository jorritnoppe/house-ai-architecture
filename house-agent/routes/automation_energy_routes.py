from __future__ import annotations

from flask import Blueprint, jsonify

from services.automation_energy_service import automation_energy_service


automation_energy_bp = Blueprint("automation_energy", __name__)


@automation_energy_bp.get("/ai/automation/excess_energy_ready")
def excess_energy_ready():
    try:
        result = automation_energy_service.get_excess_energy_ready()
        return jsonify(result), 200
    except Exception as exc:
        return jsonify(
            {
                "status": "error",
                "ready": False,
                "safe_to_use": False,
                "level": "none",
                "available_kw": 0.0,
                "reason": f"Failed to evaluate excess energy readiness: {exc}",
            }
        ), 500
