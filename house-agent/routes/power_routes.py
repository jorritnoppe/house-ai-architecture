from flask import Blueprint, jsonify

from services.power_service import (
    get_power_now_data,
    get_energy_summary_data,
    get_phase_overview_data,
    get_energy_today_data,
)

power_bp = Blueprint("power", __name__)


@power_bp.get("/ai/power_now")
def ai_power_now():
    return jsonify(get_power_now_data())


@power_bp.get("/ai/energy_summary")
def ai_energy_summary():
    return jsonify(get_energy_summary_data())


@power_bp.get("/ai/phase_overview")
def ai_phase_overview():
    return jsonify(get_phase_overview_data())


@power_bp.get("/ai/energy_today")
def ai_energy_today():
    return jsonify(get_energy_today_data())
