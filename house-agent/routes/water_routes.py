from flask import Blueprint, jsonify

from services.influx_helpers import iso_now
from services.water_service import (
    get_salt_tank_level,
    get_water_temperature_summary,
    get_water_softener_overview,
)

water_bp = Blueprint("water", __name__)


@water_bp.get("/ai/salt_tank_level")
def ai_salt_tank_level():
    data = get_salt_tank_level()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": data.get("message", "No salt tank level data found"),
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })


@water_bp.get("/ai/water_temperatures")
def ai_water_temperatures():
    data = get_water_temperature_summary()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": data.get("message", "No water temperature data found"),
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })


@water_bp.get("/ai/water_softener_overview")
def ai_water_softener_overview():
    data = get_water_softener_overview()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": data.get("message", "No water softener data found"),
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })
