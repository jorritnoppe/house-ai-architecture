from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.node_capability_service import (
    build_node_capability_summary,
    get_best_mic_node,
    get_best_speaker_node,
)

node_capability_bp = Blueprint("node_capability_bp", __name__)


@node_capability_bp.route("/ai/nodes/capabilities", methods=["GET"])
def ai_nodes_capabilities():
    return jsonify(build_node_capability_summary())


@node_capability_bp.route("/ai/nodes/best-mic", methods=["GET"])
def ai_best_mic():
    room_id = request.args.get("room")
    return jsonify({
        "status": "ok",
        "room": room_id,
        "node": get_best_mic_node(room_id),
    })


@node_capability_bp.route("/ai/nodes/best-speaker", methods=["GET"])
def ai_best_speaker():
    room_id = request.args.get("room")
    return jsonify({
        "status": "ok",
        "room": room_id,
        "node": get_best_speaker_node(room_id),
    })
