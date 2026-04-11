from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.voice_node_registry_service import get_voice_node_registry

voice_node_bp = Blueprint("voice_node_bp", __name__)


@voice_node_bp.route("/nodes/heartbeat", methods=["POST"])
def nodes_heartbeat():
    payload = request.get_json(silent=True) or {}
    try:
        result = get_voice_node_registry().heartbeat(payload)
        return jsonify({
            "status": "ok",
            "node": result,
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 400


@voice_node_bp.route("/nodes/status", methods=["GET"])
def nodes_status():
    try:
        result = get_voice_node_registry().get_summary()
        return jsonify(result)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500
