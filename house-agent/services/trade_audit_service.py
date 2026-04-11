from __future__ import annotations

import os
from typing import Any, Dict, List

from extensions import query_api


TRADE_AUDIT_BUCKET = os.getenv("TRADE_AUDIT_BUCKET", "AI_crypto")
TRADE_AUDIT_MEASUREMENT = os.getenv("TRADE_AUDIT_MEASUREMENT", "trade_audit")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def get_recent_trade_audit(limit: int = 20) -> Dict[str, Any]:
    limit = max(1, min(int(limit), 100))

    flux = f'''
from(bucket: "{TRADE_AUDIT_BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "{TRADE_AUDIT_MEASUREMENT}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})
'''

    tables = query_api.query(flux)

    items: List[Dict[str, Any]] = []

    for table in tables:
        for record in table.records:
            values = record.values or {}

            item = {
                "time": record.get_time().isoformat() if record.get_time() else None,
                "source": values.get("source"),
                "event_type": values.get("event_type"),
                "status": values.get("status"),
                "side": values.get("side"),
                "market": values.get("market"),
                "symbol": values.get("symbol"),
                "quote": values.get("quote"),
                "preview_id": values.get("preview_id"),
                "preview_price": _safe_float(values.get("preview_price")),
                "eur_amount": _safe_float(values.get("eur_amount")),
                "asset_amount": _safe_float(values.get("asset_amount")),
                "filled_amount": _safe_float(values.get("filled_amount")),
                "filled_amount_quote": _safe_float(values.get("filled_amount_quote")),
                "fee_paid": _safe_float(values.get("fee_paid")),
                "fee_currency": values.get("fee_currency"),
                "bitvavo_order_id": values.get("bitvavo_order_id"),
                "operator_id": values.get("operator_id"),
                "error_message": values.get("error_message"),
            }
            items.append(item)

    return {
        "status": "ok",
        "count": len(items),
        "items": items,
    }
