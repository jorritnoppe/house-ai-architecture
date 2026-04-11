from __future__ import annotations

import os
from typing import Any, Dict, Optional

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


TRADE_AUDIT_BUCKET = os.getenv("TRADE_AUDIT_BUCKET", "AI_crypto")
TRADE_AUDIT_MEASUREMENT = os.getenv("TRADE_AUDIT_MEASUREMENT", "trade_audit")


def log_trade_event(event: Dict[str, Any]) -> Dict[str, Any]:
    influx_url = os.getenv("INFLUX_URL")
    influx_token = os.getenv("INFLUX_TOKEN")
    influx_org = os.getenv("INFLUX_ORG")

    if not influx_url or not influx_token or not influx_org:
        return {
            "status": "error",
            "message": "missing INFLUX_URL / INFLUX_TOKEN / INFLUX_ORG",
        }

    try:
        point = Point(TRADE_AUDIT_MEASUREMENT)

        def _tag(name: str, value: Optional[Any]):
            if value is not None and str(value).strip():
                point.tag(name, str(value))

        def _field(name: str, value: Optional[Any]):
            if value is None:
                return
            if isinstance(value, bool):
                point.field(name, value)
            elif isinstance(value, int):
                point.field(name, value)
            elif isinstance(value, float):
                point.field(name, value)
            else:
                point.field(name, str(value))

        _tag("source", event.get("source", "house_agent"))
        _tag("event_type", event.get("event_type"))
        _tag("status", event.get("status"))
        _tag("side", event.get("side"))
        _tag("market", event.get("market"))

        _field("symbol", event.get("symbol"))
        _field("quote", event.get("quote"))
        _field("preview_id", event.get("preview_id"))
        _field("preview_price", event.get("preview_price"))
        _field("eur_amount", event.get("eur_amount"))
        _field("asset_amount", event.get("asset_amount"))
        _field("filled_amount", event.get("filled_amount"))
        _field("filled_amount_quote", event.get("filled_amount_quote"))
        _field("fee_paid", event.get("fee_paid"))
        _field("fee_currency", event.get("fee_currency"))
        _field("bitvavo_order_id", event.get("bitvavo_order_id"))
        _field("operator_id", event.get("operator_id"))
        _field("error_message", event.get("error_message"))
        _field("raw_json", event.get("raw_json"))

        with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=TRADE_AUDIT_BUCKET, org=influx_org, record=point)

        return {"status": "ok"}

    except Exception as exc:
        return {"status": "error", "message": str(exc)}
