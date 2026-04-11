from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.audio_validation_service import (
    build_timing_health_summary,
    load_last_timing_result,
    run_and_cache_timing_test,
)

audio_validation_bp = Blueprint("audio_validation", __name__)


@audio_validation_bp.route("/ai/audio_timing_health", methods=["GET"])
def ai_audio_timing_health():
    return jsonify(build_timing_health_summary())


@audio_validation_bp.route("/ai/audio_timing_last", methods=["GET"])
def ai_audio_timing_last():
    return jsonify(load_last_timing_result())


@audio_validation_bp.route("/ai/audio_timing_run", methods=["POST"])
def ai_audio_timing_run():
    payload = request.get_json(silent=True) or {}

    target = str(payload.get("target", "desk")).strip() or "desk"
    volume = int(payload.get("volume", 60))
    probe_seconds_back = int(payload.get("probe_seconds_back", 18))
    probe_label = str(payload.get("probe_label", "timing_test")).strip() or "timing_test"

    result = run_and_cache_timing_test(
        target=target,
        volume=volume,
        probe_seconds_back=probe_seconds_back,
        probe_label=probe_label,
    )
    return jsonify(result)


@audio_validation_bp.route("/ai/audio_output_confidence", methods=["GET"])
def ai_audio_output_confidence():
    summary = build_timing_health_summary()

    if summary.get("status") != "ok":
        return jsonify({
            "status": "error",
            "confidence": "unknown",
            "reason": "no valid timing summary available",
            "timing_health": summary,
        })

    health = summary.get("health")
    beep_count = summary.get("beep_count") or 0
    avg_interval = summary.get("avg_interval_sec")

    confidence = "low"
    if health == "healthy" and beep_count >= 5 and avg_interval is not None and 0.95 <= avg_interval <= 1.05:
        confidence = "high"
    elif health in {"healthy", "warning"} and beep_count >= 3:
        confidence = "medium"

    return jsonify({
        "status": "ok",
        "confidence": confidence,
        "reason": "derived from latest speaker timing validation",
        "timing_health": summary,
    })
