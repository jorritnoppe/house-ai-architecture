from flask import Blueprint, jsonify

from services.status_service import build_status_report
from services.announce_service import announce_text


status_bp = Blueprint("status", __name__)


@status_bp.get("/status/full")
def status_full():
    report = build_status_report()
    http_code = 200 if report["ok"] else 503
    return jsonify(report), http_code


@status_bp.post("/status/announce")
def status_announce():
    report = build_status_report()
    announce_result = announce_text(report["speech_text"])

    result = {
        **report,
        "announcement": announce_result
    }

    http_code = 200 if report["ok"] and announce_result.get("ok") else 503
    return jsonify(result), http_code


@status_bp.get("/tools/ping")
def tools_ping():
    return jsonify({
        "ok": True,
        "service": "house-agent"
    }), 200
