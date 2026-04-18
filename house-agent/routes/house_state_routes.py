from __future__ import annotations

from flask import Blueprint, jsonify

from services.house_state_service import get_house_state, get_daily_house_summary
from services.waste_schedule_service import get_waste_schedule_summary
from services.morning_briefing_service import get_morning_briefing
from services.evening_briefing_service import get_evening_briefing

house_state_bp = Blueprint("house_state_bp", __name__)


@house_state_bp.route("/ai/house_state", methods=["GET"])
def ai_house_state():
    try:
        return jsonify(get_house_state())
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500


@house_state_bp.route("/ai/daily_house_summary", methods=["GET"])
def ai_daily_house_summary():
    try:
        return jsonify(get_daily_house_summary())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@house_state_bp.route("/ai/waste_schedule_summary", methods=["GET"])
def ai_waste_schedule_summary():
    try:
        return jsonify(get_waste_schedule_summary())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@house_state_bp.route("/ai/morning_briefing", methods=["GET"])
def ai_morning_briefing():
    try:
        return jsonify(get_morning_briefing())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@house_state_bp.route("/ai/evening_briefing", methods=["GET"])
def ai_evening_briefing():
    try:
        return jsonify(get_evening_briefing())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
