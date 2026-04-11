from flask import Blueprint, jsonify, request

from services.loxone_action_service import (
    audio_node_power,
    audio_speaker_route,
    audio_party,
    audio_playback,
)

audio_tools_bp = Blueprint("audio_tools", __name__)


@audio_tools_bp.route("/tools/audio/node_power/<state>", methods=["POST"])
def tools_audio_node_power(state):
    room = request.args.get("room", "").strip()
    if state not in ("on", "off"):
        return jsonify({"status": "error", "message": "State must be on or off"}), 400
    if not room:
        return jsonify({"status": "error", "message": "Missing room"}), 400

    result = audio_node_power(room, state)
    return jsonify(result), (200 if result.get("status") == "ok" else 400)


@audio_tools_bp.route("/tools/audio/speaker_route/<state>", methods=["POST"])
def tools_audio_speaker_route(state):
    target = request.args.get("target", "").strip()
    if state not in ("on", "off", "enable", "disable"):
        return jsonify({"status": "error", "message": "State must be on/off/enable/disable"}), 400
    if not target:
        return jsonify({"status": "error", "message": "Missing target"}), 400

    normalized = "on" if state in ("on", "enable") else "off"
    result = audio_speaker_route(target, normalized)
    return jsonify(result), (200 if result.get("status") == "ok" else 400)


@audio_tools_bp.route("/tools/audio/party/<state>", methods=["POST"])
def tools_audio_party(state):
    if state not in ("on", "off"):
        return jsonify({"status": "error", "message": "State must be on or off"}), 400

    result = audio_party(state)
    return jsonify(result), (200 if result.get("status") == "ok" else 400)


@audio_tools_bp.route("/tools/audio/playback/<state>", methods=["POST"])
def tools_audio_playback(state):
    room = request.args.get("room", "").strip()
    if state not in ("on", "off"):
        return jsonify({"status": "error", "message": "State must be on or off"}), 400
    if not room:
        return jsonify({"status": "error", "message": "Missing room"}), 400

    result = audio_playback(room, state)
    return jsonify(result), (200 if result.get("status") == "ok" else 400)
