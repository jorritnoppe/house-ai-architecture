from flask import Blueprint, jsonify, request

from services.lms_music_service import play_ai_house_music, stop_room_music

music_bp = Blueprint("music_bp", __name__)


@music_bp.route("/tools/music/play_ai_house", methods=["POST"])
def route_play_ai_house():
    payload = request.get_json(silent=True) or {}
    target = payload.get("target", "living")
    result = play_ai_house_music(target)
    return jsonify(result), 200 if result.get("status") == "ok" else 400


@music_bp.route("/tools/music/stop_room", methods=["POST"])
def route_stop_room():
    payload = request.get_json(silent=True) or {}
    target = payload.get("target", "living")
    result = stop_room_music(target)
    return jsonify(result), 200 if result.get("status") == "ok" else 400
