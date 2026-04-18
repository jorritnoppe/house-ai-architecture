from flask import Blueprint, jsonify, render_template, request

from services.lms_music_service import play_ai_house_music, stop_room_music
from services.music_library_service import (
    delete_track,
    get_music_library,
    refresh_music_library,
    set_track_enabled,
)

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


@music_bp.route("/ai-server/music", methods=["GET"])
def music_admin_page():
    return render_template("music_admin.html")


@music_bp.route("/ai-server/music/api/library", methods=["GET"])
def music_library_api():
    result = get_music_library()
    return jsonify(result), 200 if result.get("status") == "ok" else 400


@music_bp.route("/ai-server/music/api/refresh", methods=["POST"])
def music_refresh_api():
    result = refresh_music_library()
    return jsonify(result), 200 if result.get("status") == "ok" else 400


@music_bp.route("/ai-server/music/api/toggle", methods=["POST"])
def music_toggle_api():
    payload = request.get_json(silent=True) or {}
    relative_path = payload.get("relative_path", "")
    enabled = bool(payload.get("enabled", False))
    result = set_track_enabled(relative_path=relative_path, enabled=enabled)
    return jsonify(result), 200 if result.get("status") == "ok" else 400


@music_bp.route("/ai-server/music/api/delete", methods=["POST"])
def music_delete_api():
    payload = request.get_json(silent=True) or {}
    relative_path = payload.get("relative_path", "")
    result = delete_track(relative_path=relative_path)
    return jsonify(result), 200 if result.get("status") == "ok" else 400
