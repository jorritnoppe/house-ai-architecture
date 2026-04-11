from flask import Blueprint, jsonify

music_controls_bp = Blueprint("music_controls", __name__)

MUSIC_STATE = {
    "Music_Living_ON": 0,
    "Music_Living_OFF": 0,
    "Music_toilet_ON": 0,
    "Music_toilet_OFF": 0,
    "Music_party_ON": 0,
    "Music_party_OFF": 0,
}


def build_plaintext_payload() -> str:
    return "\n".join(f"{key}:{value}" for key, value in MUSIC_STATE.items())


def set_music_state(command_key: str, value: int) -> dict:
    if command_key not in MUSIC_STATE:
        return {
            "ok": False,
            "error": f"Unknown command: {command_key}",
            "available_commands": list(MUSIC_STATE.keys()),
        }

    MUSIC_STATE[command_key] = int(value)

    return {
        "ok": True,
        "updated": command_key,
        "value": MUSIC_STATE[command_key],
        "state": MUSIC_STATE.copy(),
        "raw_message": build_plaintext_payload(),
    }


@music_controls_bp.route("/AI_Music_Controls/", methods=["GET"])
def ai_music_controls_feed():
    return build_plaintext_payload(), 200, {"Content-Type": "text/plain; charset=utf-8"}


@music_controls_bp.route("/tools/music/living/on", methods=["POST"])
def music_living_on():
    return jsonify(set_music_state("Music_Living_ON", 1)), 200


@music_controls_bp.route("/tools/music/living/off", methods=["POST"])
def music_living_off():
    return jsonify(set_music_state("Music_Living_OFF", 1)), 200


@music_controls_bp.route("/tools/music/toilet/on", methods=["POST"])
def music_toilet_on():
    return jsonify(set_music_state("Music_toilet_ON", 1)), 200


@music_controls_bp.route("/tools/music/toilet/off", methods=["POST"])
def music_toilet_off():
    return jsonify(set_music_state("Music_toilet_OFF", 1)), 200


@music_controls_bp.route("/tools/music/party/on", methods=["POST"])
def music_party_on():
    return jsonify(set_music_state("Music_party_ON", 1)), 200


@music_controls_bp.route("/tools/music/party/off", methods=["POST"])
def music_party_off():
    return jsonify(set_music_state("Music_party_OFF", 1)), 200


@music_controls_bp.route("/tools/music/reset", methods=["POST"])
def music_reset():
    for key in MUSIC_STATE:
        MUSIC_STATE[key] = 0

    return jsonify({
        "ok": True,
        "message": "All music flags reset to 0",
        "state": MUSIC_STATE.copy(),
        "raw_message": build_plaintext_payload(),
    }), 200


@music_controls_bp.route("/tools/music/status", methods=["GET"])
def music_status():
    return jsonify({
        "ok": True,
        "service": "loxone_music_http_feed",
        "feed_url": "/AI_Music_Controls/",
        "state": MUSIC_STATE.copy(),
        "raw_message": build_plaintext_payload(),
    }), 200
