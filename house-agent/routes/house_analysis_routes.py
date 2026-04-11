from flask import Blueprint, jsonify

from services.house_analysis_service import (
    get_house_facts_now,
    get_house_facts_today,
    get_house_briefing_now,
    get_house_briefing_today,
)

house_analysis_bp = Blueprint("house_analysis", __name__)


@house_analysis_bp.get("/ai/house_facts_now")
def ai_house_facts_now():
    return jsonify(get_house_facts_now())


@house_analysis_bp.get("/ai/house_facts_today")
def ai_house_facts_today():
    return jsonify(get_house_facts_today())


@house_analysis_bp.get("/ai/house_briefing_now")
def ai_house_briefing_now():
    return jsonify(get_house_briefing_now())


@house_analysis_bp.get("/ai/house_briefing_today")
def ai_house_briefing_today():
    return jsonify(get_house_briefing_today())
