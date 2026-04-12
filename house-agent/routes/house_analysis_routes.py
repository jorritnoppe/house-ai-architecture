from flask import Blueprint, jsonify

from services.house_analysis_service import (
    get_house_briefing_now,
    get_house_briefing_today,
    get_house_facts_now,
    get_house_facts_today,
)

house_analysis_bp = Blueprint("house_analysis", __name__)


@house_analysis_bp.route("/ai/house_briefing_now", methods=["GET"])
def ai_house_briefing_now():
    return jsonify(get_house_briefing_now())


@house_analysis_bp.route("/ai/house_briefing_today", methods=["GET"])
def ai_house_briefing_today():
    return jsonify(get_house_briefing_today())


@house_analysis_bp.route("/ai/house_facts_now", methods=["GET"])
def ai_house_facts_now():
    return jsonify(get_house_facts_now())


@house_analysis_bp.route("/ai/house_facts_today", methods=["GET"])
def ai_house_facts_today():
    return jsonify(get_house_facts_today())
