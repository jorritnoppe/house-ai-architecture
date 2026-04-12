from flask import Blueprint, jsonify, request

from services.service_health_service import (
    get_local_service_health,
    get_service_health_for_node,
    get_services_overview,
)

service_health_bp = Blueprint("service_health_bp", __name__)


@service_health_bp.route("/ai/service/health", methods=["GET"])
def ai_service_health():
    try:
        return jsonify({
            "status": "ok",
            "data": get_local_service_health()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@service_health_bp.route("/ai/service/summary", methods=["GET"])
def ai_service_summary():
    node = request.args.get("node", "ai-server")
    try:
        return jsonify({
            "status": "ok",
            "data": get_service_health_for_node(node)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@service_health_bp.route("/ai/services/overview", methods=["GET"])
def ai_services_overview():
    try:
        return jsonify({
            "status": "ok",
            "data": get_services_overview()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
