from flask import Blueprint, jsonify

from services.sma_service import (
    get_sma_summary_data,
    get_sma_production_overview_data,
)

sma_bp = Blueprint("sma", __name__)


@sma_bp.get("/ai/sma_summary")
def ai_sma_summary():
    return jsonify(get_sma_summary_data())


@sma_bp.get("/ai/sma_production_overview")
def ai_sma_production_overview():
    return jsonify(get_sma_production_overview_data())
