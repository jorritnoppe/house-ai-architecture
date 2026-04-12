from flask import Blueprint, jsonify

from services.energy_service import energy_service

energy_bp = Blueprint("energy_bp", __name__, url_prefix="/ai")


@energy_bp.route("/unified_energy_snapshot", methods=["GET"])
def unified_energy_snapshot():
    try:
        return jsonify(energy_service.get_live_snapshot())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get unified energy snapshot: {str(e)}"
        }), 500


@energy_bp.route("/unified_energy_summary", methods=["GET"])
def unified_energy_summary():
    try:
        return jsonify(energy_service.get_energy_ai_summary())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get unified energy summary: {str(e)}"
        }), 500
