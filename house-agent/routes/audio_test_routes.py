from flask import Blueprint, jsonify

from services.audio_test_pattern import save_test_pattern

bp = Blueprint("audio_test", __name__)


@bp.route("/audio/test_pattern", methods=["POST"])
def audio_test_pattern():
    result = save_test_pattern()
    url = f"http://192.168.9.182:8000/voice/files/{result['filename']}"

    return jsonify({
        "status": "ok",
        "file": result,
        "url": url,
    })
