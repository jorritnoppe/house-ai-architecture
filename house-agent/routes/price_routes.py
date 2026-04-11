from flask import Blueprint, jsonify

from config import PRICE_INFLUX_BUCKET, PRICE_INFLUX_MEASUREMENT, PRICE_INFLUX_FIELD
from services.influx_helpers import iso_now
from services.price_service import (
    query_latest_price,
    get_electricity_cost_today,
    get_electricity_cost_last_24h,
    get_cheapest_hours_today,
)

price_bp = Blueprint("price", __name__)


@price_bp.get("/ai/electricity_price_now")
def ai_electricity_price_now():
    latest = query_latest_price(range_window="-7d")

    if not latest:
        return jsonify({
            "status": "error",
            "message": "No electricity price data found",
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        "price_eur_per_kwh": latest["value"],
        "price_time": latest["time"],
        "source": {
            "bucket": PRICE_INFLUX_BUCKET,
            "measurement": PRICE_INFLUX_MEASUREMENT,
            "field": PRICE_INFLUX_FIELD,
        },
    })


@price_bp.get("/ai/electricity_cost_today")
def ai_electricity_cost_today():
    data = get_electricity_cost_today()
    return jsonify({
        "status": data["status"],
        "timestamp": iso_now(),
        **data,
    })


@price_bp.get("/ai/electricity_cost_last_24h")
def ai_electricity_cost_last_24h():
    data = get_electricity_cost_last_24h()
    return jsonify({
        "status": data["status"],
        "timestamp": iso_now(),
        **data,
    })


@price_bp.get("/ai/cheapest_hours_today")
def ai_cheapest_hours_today():
    data = get_cheapest_hours_today(limit=3)
    return jsonify({
        "status": data["status"],
        "timestamp": iso_now(),
        **data,
    })
