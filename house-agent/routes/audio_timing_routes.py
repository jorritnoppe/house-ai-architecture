from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.audio_timing_test_service import run_timing_test

audio_timing_bp = Blueprint("audio_timing", __name__)


@audio_timing_bp.route("/feedback-probe/run_timing_test", methods=["POST"])
def feedback_probe_run_timing_test():
    payload = request.get_json(silent=True) or {}

    target = payload.get("target", "desk")
    volume = int(payload.get("volume", 60))
    probe_seconds_back = int(payload.get("probe_seconds_back", 10))
    probe_label = payload.get("probe_label", "timing_test")

    try:
        result = run_timing_test(
            target=target,
            volume=volume,
            probe_seconds_back=probe_seconds_back,
            probe_label=probe_label,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500
