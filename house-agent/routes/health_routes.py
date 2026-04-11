from flask import Blueprint, jsonify

from config import INFLUX_BUCKET
from extensions import app, query_api
from services.influx_helpers import iso_now

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    try:
        flux = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -5m) |> limit(n:1)'
        query_api.query(flux)
        status = "ok"
    except Exception as exc:
        status = "error"
        app.logger.exception("Health check failed: %s", exc)

    return jsonify({
        "service": "house-agent",
        "bucket": INFLUX_BUCKET,
        "status": status,
        "time": iso_now(),
    })
