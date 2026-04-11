from __future__ import annotations
from flask import Blueprint, jsonify, request

import tempfile
from pathlib import Path


from services.feedback_probe_client import (
    probe_health,
    probe_audio_window,
    probe_save_window,
    probe_list_recent,
    transcribe_saved_probe_file,
    update_probe_metadata,
    flag_probe_capture,
    score_probe_capture,
    probe_download_file,
)


from services.stt_service import transcribe_wav

feedback_probe_bp = Blueprint("feedback_probe", __name__)

@feedback_probe_bp.route("/feedback-probe/score_capture", methods=["POST"])
def feedback_probe_score_capture():
    payload = request.get_json(silent=True) or {}
    main_transcript = payload.get("main_transcript", "")
    probe_transcript = payload.get("probe_transcript", "")
    rms = payload.get("rms")

    result = score_probe_capture(
        main_transcript=main_transcript,
        probe_transcript=probe_transcript,
        rms=rms,
    )
    return jsonify(result)


@feedback_probe_bp.route("/feedback-probe/annotate_saved", methods=["POST"])
def feedback_probe_annotate_saved():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    patch = payload.get("patch") or {}

    result = update_probe_metadata(path, patch)
    status_code = 200 if result.get("status") == "ok" else 400
    return jsonify(result), status_code


@feedback_probe_bp.route("/feedback-probe/flag_saved", methods=["POST"])
def feedback_probe_flag_saved():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    reason = payload.get("reason", "unknown")

    result = flag_probe_capture(path, reason)
    status_code = 200 if result.get("status") == "ok" else 400
    return jsonify(result), status_code


@feedback_probe_bp.route("/feedback-probe/score_and_flag", methods=["POST"])
def feedback_probe_score_and_flag():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    main_transcript = payload.get("main_transcript", "")

    transcribe_result = transcribe_saved_probe_file(path)
    if transcribe_result.get("status") != "ok":
        return jsonify(transcribe_result), 400

    probe_transcript = transcribe_result.get("transcript", "")
    rms = payload.get("rms")
    score = score_probe_capture(
        main_transcript=main_transcript,
        probe_transcript=probe_transcript,
        rms=rms,
    )

    annotation = {
        "main_transcript": main_transcript,
        "probe_transcript": probe_transcript,
        "score": score,
    }
    annotate_result = update_probe_metadata(path, annotation)

    flag_result = None
    if score.get("classification") in {"low_signal", "empty_probe_transcript", "possible_stt_mismatch"}:
        flag_result = flag_probe_capture(path, score["classification"])

    return jsonify({
        "status": "ok",
        "transcribe_result": transcribe_result,
        "score": score,
        "annotate_result": annotate_result,
        "flag_result": flag_result,
    })


@feedback_probe_bp.get("/feedback-probe/health")
def feedback_probe_health():
    try:
        return jsonify(probe_health())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@feedback_probe_bp.post("/feedback-probe/window")
def feedback_probe_window():
    payload = request.get_json(silent=True) or {}
    seconds_back = int(payload.get("seconds_back", 5))
    try:
        return jsonify(probe_audio_window(seconds_back=seconds_back))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@feedback_probe_bp.post("/feedback-probe/save_window")
def feedback_probe_save_window():
    payload = request.get_json(silent=True) or {}
    seconds_back = int(payload.get("seconds_back", 8))
    label = str(payload.get("label", "feedback_probe")).strip() or "feedback_probe"
    metadata = payload.get("metadata") or {}

    try:
        return jsonify(
            probe_save_window(
                seconds_back=seconds_back,
                label=label,
                metadata=metadata,
            )
        )
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@feedback_probe_bp.get("/feedback-probe/list_recent")
def feedback_probe_list_recent():
    limit = int(request.args.get("limit", 20))
    try:
        return jsonify(probe_list_recent(limit=limit))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@feedback_probe_bp.post("/feedback-probe/flag_file")
def feedback_probe_flag_file():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    reason = str(payload.get("reason", "review")).strip() or "review"

    try:
        return jsonify(probe_flag_file(path=path, reason=reason))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@feedback_probe_bp.get("/feedback-probe/list_flagged")
def feedback_probe_list_flagged():
    limit = int(request.args.get("limit", 20))
    try:
        return jsonify(probe_list_flagged(limit=limit))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@feedback_probe_bp.post("/feedback-probe/transcribe_saved")
def feedback_probe_transcribe_saved():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    language = payload.get("language", "en")

    if not path:
        return jsonify({"status": "error", "error": "missing path"}), 400

    tmp_path = None
    try:
        raw = probe_download_file(path)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)

        result = transcribe_wav(str(tmp_path), language=language)

        return jsonify({
            "status": "ok",
            "path": path,
            "transcript": result.get("text", ""),
            "language": result.get("language"),
            "language_probability": result.get("language_probability"),
            "mono_file": result.get("mono_file"),
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


@feedback_probe_bp.post("/feedback-probe/compare_transcripts")
def feedback_probe_compare_transcripts():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    main_transcript = (payload.get("main_transcript") or "").strip()
    language = payload.get("language", "en")

    if not path:
        return jsonify({"status": "error", "error": "missing path"}), 400

    try:
        probe_result = feedback_probe_transcribe_saved_internal(path=path, language=language)
        probe_transcript = (probe_result.get("transcript") or "").strip()

        same = main_transcript.lower() == probe_transcript.lower()
        main_words = set(main_transcript.lower().split())
        probe_words = set(probe_transcript.lower().split())
        overlap = len(main_words & probe_words)
        union = len(main_words | probe_words) if (main_words | probe_words) else 0
        similarity = round((overlap / union), 3) if union else 1.0

        return jsonify({
            "status": "ok",
            "path": path,
            "main_transcript": main_transcript,
            "probe_transcript": probe_transcript,
            "exact_match": same,
            "word_overlap_similarity": similarity,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


def feedback_probe_transcribe_saved_internal(path: str, language: str = "en") -> dict:
    tmp_path = None
    try:
        raw = probe_download_file(path)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)

        result = transcribe_wav(str(tmp_path), language=language)

        return {
            "status": "ok",
            "path": path,
            "transcript": result.get("text", ""),
            "language": result.get("language"),
            "language_probability": result.get("language_probability"),
            "mono_file": result.get("mono_file"),
        }
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
