from flask import Blueprint, jsonify, request

from services.loxone_service import (
    get_loxone_structure_summary,
    get_all_controls,
    get_controls_by_room,
    get_controls_by_category,
)

loxone_bp = Blueprint("loxone", __name__)


@loxone_bp.route("/ai/loxone_structure_summary", methods=["GET"])
def loxone_structure_summary():
    return jsonify(get_loxone_structure_summary())


@loxone_bp.route("/ai/loxone_controls", methods=["GET"])
def loxone_controls():
    return jsonify(get_all_controls())


@loxone_bp.route("/ai/loxone_controls_by_room", methods=["GET"])
def loxone_controls_by_room():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing room parameter"}), 400
    return jsonify(get_controls_by_room(room))


@loxone_bp.route("/ai/loxone_controls_by_category", methods=["GET"])
def loxone_controls_by_category():
    category = request.args.get("category", "").strip()
    if not category:
        return jsonify({"status": "error", "message": "Missing category parameter"}), 400
    return jsonify(get_controls_by_category(category))


