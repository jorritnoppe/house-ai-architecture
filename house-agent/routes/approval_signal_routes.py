from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app

from services.approval_session_service import get_approval_session_service
from services.approval_signal_processor_service import get_approval_signal_processor_service

approval_signal_bp = Blueprint("approval_signal_bp", __name__)


@approval_signal_bp.route("/ai/approvals/signal/states", methods=["GET"])
def approval_signal_states():
    try:
        return jsonify(get_approval_signal_processor_service().list_states())
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
        }), 500


@approval_signal_bp.route("/ai/approvals/signal/process", methods=["POST"])
def approval_signal_process():
    raw_body = request.get_data(as_text=True)
    payload = request.get_json(silent=True)

    current_app.logger.warning("APPROVAL_SIGNAL_DEBUG headers=%s", dict(request.headers))
    current_app.logger.warning("APPROVAL_SIGNAL_DEBUG raw_body=%r", raw_body)
    current_app.logger.warning("APPROVAL_SIGNAL_DEBUG json=%r", payload)
    current_app.logger.warning("APPROVAL_SIGNAL_DEBUG args=%r", request.args.to_dict(flat=True))
    current_app.logger.warning("APPROVAL_SIGNAL_DEBUG form=%r", request.form.to_dict(flat=True))

    if not isinstance(payload, dict):
        payload = {}

    source = str(
        payload.get("source")
        or request.args.get("source")
        or request.form.get("source")
        or ""
    ).strip()

    signal = str(
        payload.get("signal")
        or request.args.get("signal")
        or request.form.get("signal")
        or ""
    ).strip()

    value = payload.get(
        "value",
        request.args.get("value", request.form.get("value"))
    )

    try:
        result = get_approval_signal_processor_service().process_signal(
            source=source,
            signal=signal,
            value=value,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc),
            "source": source,
            "signal": signal,
            "value": value,
        }), 400


@approval_signal_bp.route("/ai/approvals/sessions", methods=["GET"])
def approval_sessions():
    try:
        return jsonify(get_approval_session_service().list_active())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500

