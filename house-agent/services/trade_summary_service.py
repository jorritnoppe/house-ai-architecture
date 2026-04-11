from __future__ import annotations

from typing import Any, Dict, List
import xml.etree.ElementTree as ET


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _extract_market_rows(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("<"):
            try:
                root = ET.fromstring(raw)
                rows: List[Dict[str, Any]] = []
                for market in root.findall(".//market"):
                    rows.append({
                        "market": (market.findtext("name") or "").strip().upper(),
                        "base": (market.findtext("base") or "").strip().upper(),
                        "quote": (market.findtext("quote") or "").strip().upper(),
                        "price": market.findtext("price"),
                    })
                return rows
            except Exception:
                return []

    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    if not isinstance(raw, dict):
        return []

    for key in ("markets", "items", "result", "data", "assets"):
        value = raw.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]

    return []


def _extract_market_name(row: Dict[str, Any]) -> str:
    for key in ("market", "symbol", "name", "id"):
        value = row.get(key)
        if value:
            return str(value).strip().upper()

    base = str(row.get("base") or "").strip().upper()
    quote = str(row.get("quote") or "").strip().upper()
    if base and quote:
        return f"{base}-{quote}"

    return ""


def _extract_market_price(row: Dict[str, Any]) -> float:
    for key in (
        "price",
        "last",
        "lastPrice",
        "rate",
        "value",
        "current_price",
        "currentPrice",
        "close",
        "ask",
        "bid",
    ):
        if row.get(key) is not None:
            return _to_float(row.get(key), 0.0)
    return 0.0


def build_holdings_summary(
    balances: List[Dict[str, Any]],
    market_rows: Any,
    lock_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    extracted_market_rows = _extract_market_rows(market_rows)

    market_price_map: Dict[str, float] = {}
    for row in extracted_market_rows:
        market = _extract_market_name(row)
        if not market:
            continue
        market_price_map[market] = _extract_market_price(row)

    lock_map: Dict[str, Dict[str, Any]] = {}
    for row in lock_rows or []:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        lock_map[symbol] = row

    holdings: List[Dict[str, Any]] = []
    total_eur_value = 0.0

    for row in balances or []:
        symbol = str(row.get("symbol") or row.get("asset") or "").strip().upper()
        amount = _to_float(
            row.get("available")
            if row.get("available") is not None
            else row.get("balance")
        )

        if not symbol or amount <= 0:
            continue

        if symbol == "EUR":
            market = "EUR-EUR"
            eur_price = 1.0
        else:
            market = f"{symbol}-EUR"
            eur_price = _to_float(market_price_map.get(market), 0.0)

        eur_value = round(amount * eur_price, 8)

        lock_info = lock_map.get(symbol, {})
        locked = bool(lock_info.get("locked", False))
        lock_reason = lock_info.get("reason")

        holdings.append({
            "symbol": symbol,
            "amount": amount,
            "market": market,
            "eur_price": eur_price,
            "eur_value": eur_value,
            "locked": locked,
            "lock_reason": lock_reason,
            "strategy_managed": False,
        })

        total_eur_value += eur_value

    holdings.sort(key=lambda x: x["eur_value"], reverse=True)

    return {
        "status": "ok",
        "holdings": holdings,
        "totals": {
            "asset_count": len(holdings),
            "total_eur_value": round(total_eur_value, 2),
        },
    }
