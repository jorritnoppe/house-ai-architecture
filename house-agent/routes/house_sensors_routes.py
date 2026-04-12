from flask import Blueprint, jsonify, request

from services.house_sensors_service import get_house_sensors

house_sensors_bp = Blueprint("house_sensors_bp", __name__)


@house_sensors_bp.route("/ai/house_sensors", methods=["GET"])
def ai_house_sensors():
    minutes_raw = request.args.get("minutes", "60").strip()
    limit_raw = request.args.get("limit", "8000").strip()

    try:
        minutes = int(minutes_raw)
    except ValueError:
        minutes = 60

    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 8000

    if minutes < 1:
        minutes = 1
    if minutes > 1440:
        minutes = 1440

    if limit < 100:
        limit = 100
    if limit > 50000:
        limit = 50000

    try:
        return jsonify(get_house_sensors(minutes=minutes, limit=limit))
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500
