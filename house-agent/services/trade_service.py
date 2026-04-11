from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict

from services.bitvavo_trade_service import bitvavo_trade_service
from services.trade_log_service import log_trade_event
from services.trade_state_store import trade_state_store


TRADING_ENABLED = os.getenv("TRADING_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
TRADING_ARMED = os.getenv("TRADING_ARMED", "false").strip().lower() in ("1", "true", "yes", "on")
TRADE_PREVIEW_TTL_SECONDS = int(os.getenv("TRADE_PREVIEW_TTL_SECONDS", "120"))
TRADE_MAX_EUR = float(os.getenv("TRADE_MAX_EUR", "250"))
TRADE_MAX_SELL_AMOUNT = float(os.getenv("TRADE_MAX_SELL_AMOUNT", "1000000"))
TRADE_MAX_MANUAL_SELL_EUR = float(os.getenv("TRADE_MAX_MANUAL_SELL_EUR", "1000"))
TRADE_COOLDOWN_SECONDS = int(os.getenv("TRADE_COOLDOWN_SECONDS", "20"))

_LAST_TRADE_TS: float = 0.0


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _cleanup_previews() -> None:
    trade_state_store.cleanup_expired_previews()


def _check_cooldown() -> None:
    global _LAST_TRADE_TS
    now = time.time()
    if _LAST_TRADE_TS and (now - _LAST_TRADE_TS) < TRADE_COOLDOWN_SECONDS:
        remaining = TRADE_COOLDOWN_SECONDS - (now - _LAST_TRADE_TS)
        raise ValueError(f"trade cooldown active, wait {remaining:.1f}s")


def _resolve_sell_all_amount(symbol: str) -> float:
    balance = bitvavo_trade_service.get_balance()
    if balance.get("status") != "ok":
        raise ValueError("could not load balance for sell_all")

    assets = balance.get("assets", []) or []
    for item in assets:
        if str(item.get("symbol") or "").strip().upper() == symbol:
            available = _safe_float(item.get("available"), 0.0) or 0.0
            if available <= 0:
                raise ValueError(f"no available balance for {symbol}")
            return float(available)

    raise ValueError(f"no available balance found for {symbol}")


def _validate_sell_policy(preview: Dict[str, Any]) -> None:
    symbol = str(preview.get("base") or "").strip().upper()
    if not symbol:
        raise ValueError("preview missing symbol")

    lock_info = trade_state_store.get_position_lock(symbol)
    if lock_info.get("locked"):
        raise ValueError(f"{symbol} is locked and cannot be sold through manual/system trade flow")

    estimated_eur_total = _safe_float(preview.get("estimated_eur_total"), 0.0) or 0.0
    if estimated_eur_total > TRADE_MAX_MANUAL_SELL_EUR:
        raise ValueError(
            f"sell preview exceeds max allowed manual sell value of {TRADE_MAX_MANUAL_SELL_EUR:.2f} EUR"
        )


def get_trade_config() -> Dict[str, Any]:
    return {
        "status": "ok",
        "trading_enabled": TRADING_ENABLED,
        "trading_armed": TRADING_ARMED,
        "preview_ttl_seconds": TRADE_PREVIEW_TTL_SECONDS,
        "trade_max_eur": TRADE_MAX_EUR,
        "trade_max_sell_amount": TRADE_MAX_SELL_AMOUNT,
        "trade_max_manual_sell_eur": TRADE_MAX_MANUAL_SELL_EUR,
        "trade_cooldown_seconds": TRADE_COOLDOWN_SECONDS,
        "bridge_base_url": bitvavo_trade_service.base_url,
        "audit_bucket": os.getenv("TRADE_AUDIT_BUCKET", "AI_crypto"),
        "audit_measurement": os.getenv("TRADE_AUDIT_MEASUREMENT", "trade_audit"),
    }


def get_positions() -> Dict[str, Any]:
    balance = bitvavo_trade_service.get_balance()
    markets = bitvavo_trade_service.get_markets()
    locks = trade_state_store.list_position_locks()
    return {
        "status": "ok",
        "balance": balance,
        "markets": markets,
        "locks": locks,
    }


def create_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    _cleanup_previews()

    side = str(payload.get("side", "")).strip().lower()
    symbol = str(payload.get("symbol", "")).strip().upper()
    quote = str(payload.get("quote", "EUR")).strip().upper()
    market = payload.get("market")
    eur_amount = _safe_float(payload.get("eur_amount"))
    amount = _safe_float(payload.get("amount"))
    sell_all = bool(payload.get("sell_all", False))

    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")

    if not symbol and not market:
        raise ValueError("symbol or market is required")

    if side == "buy":
        if eur_amount is None and amount is None:
            raise ValueError("eur_amount or amount is required")
        if eur_amount is not None and amount is not None:
            raise ValueError("provide only one of eur_amount or amount")
    else:
        if sell_all:
            if not symbol:
                raise ValueError("symbol is required for sell_all")
            amount = _resolve_sell_all_amount(symbol)
            eur_amount = None
        else:
            if amount is None:
                raise ValueError("sell requires amount or sell_all=true")
            if eur_amount is not None:
                raise ValueError("manual sell must use amount, not eur_amount")

    if eur_amount is not None and eur_amount <= 0:
        raise ValueError("eur_amount must be > 0")

    if amount is not None and amount <= 0:
        raise ValueError("amount must be > 0")

    if eur_amount is not None and eur_amount > TRADE_MAX_EUR:
        raise ValueError(f"eur_amount exceeds max of {TRADE_MAX_EUR}")

    if side == "sell" and amount is not None and amount > TRADE_MAX_SELL_AMOUNT:
        raise ValueError(f"sell amount exceeds max of {TRADE_MAX_SELL_AMOUNT}")

    bridge_payload = {
        "side": side,
        "symbol": symbol if symbol else None,
        "market": market,
        "quote": quote,
        "eur_amount": eur_amount,
        "amount": amount,
    }

    preview = bitvavo_trade_service.preview_trade(bridge_payload)
    if preview.get("status") != "ok":
        error_message = json.dumps(preview, ensure_ascii=False)
        log_trade_event({
            "event_type": "preview_error",
            "status": "error",
            "side": side,
            "market": preview.get("market") or (f"{symbol}-{quote}" if symbol else market),
            "symbol": symbol,
            "quote": quote,
            "eur_amount": eur_amount,
            "asset_amount": amount,
            "error_message": error_message,
            "raw_json": error_message,
        })
        return preview

    if side == "sell":
        _validate_sell_policy(preview)

    preview_id = str(uuid.uuid4())
    trade_state_store.create_preview(
        preview_id=preview_id,
        ttl_seconds=TRADE_PREVIEW_TTL_SECONDS,
        request_payload=bridge_payload,
        preview_payload=preview,
    )

    log_trade_event({
        "event_type": "preview_created",
        "status": "ok",
        "side": preview.get("side"),
        "market": preview.get("market"),
        "symbol": preview.get("base"),
        "quote": preview.get("quote"),
        "preview_id": preview_id,
        "preview_price": _safe_float(preview.get("current_price")),
        "eur_amount": _safe_float(preview.get("estimated_eur_total")),
        "asset_amount": _safe_float(preview.get("estimated_amount")),
        "raw_json": json.dumps(preview, ensure_ascii=False),
    })

    return {
        "status": "ok",
        "preview_id": preview_id,
        "expires_in_seconds": TRADE_PREVIEW_TTL_SECONDS,
        "preview": preview,
    }


def confirm_trade(preview_id: str) -> Dict[str, Any]:
    global _LAST_TRADE_TS
    _cleanup_previews()

    if not TRADING_ENABLED:
        raise ValueError("trading is disabled")

    if not TRADING_ARMED:
        raise ValueError("trading is not armed")

    _check_cooldown()

    record = trade_state_store.get_preview(preview_id)
    if not record:
        raise ValueError("preview_id not found or expired")

    if str(record.get("status") or "").strip().lower() != "pending":
        raise ValueError(f"preview is not pending: {record.get('status')}")

    bridge_payload = record["request"]
    preview = record["preview"]

    if str(preview.get("side") or "").strip().lower() == "sell":
        _validate_sell_policy(preview)

    log_trade_event({
        "event_type": "confirm_requested",
        "status": "ok",
        "side": preview.get("side"),
        "market": preview.get("market"),
        "symbol": preview.get("base"),
        "quote": preview.get("quote"),
        "preview_id": preview_id,
        "preview_price": _safe_float(preview.get("current_price")),
        "eur_amount": _safe_float(preview.get("estimated_eur_total")),
        "asset_amount": _safe_float(preview.get("estimated_amount")),
        "raw_json": json.dumps(preview, ensure_ascii=False),
    })

    result = bitvavo_trade_service.execute_trade(bridge_payload)

    if result.get("status") != "ok":
        error_message = json.dumps(result, ensure_ascii=False)
        log_trade_event({
            "event_type": "execute_error",
            "status": "error",
            "side": preview.get("side"),
            "market": preview.get("market"),
            "symbol": preview.get("base"),
            "quote": preview.get("quote"),
            "preview_id": preview_id,
            "preview_price": _safe_float(preview.get("current_price")),
            "eur_amount": _safe_float(preview.get("estimated_eur_total")),
            "asset_amount": _safe_float(preview.get("estimated_amount")),
            "error_message": error_message,
            "raw_json": error_message,
        })
        return result

    bitvavo_response = result.get("bitvavo_response", {})
    _LAST_TRADE_TS = time.time()
    trade_state_store.mark_preview_consumed(preview_id)

    log_trade_event({
        "event_type": "execute_success",
        "status": "ok",
        "side": preview.get("side"),
        "market": preview.get("market"),
        "symbol": preview.get("base"),
        "quote": preview.get("quote"),
        "preview_id": preview_id,
        "preview_price": _safe_float(preview.get("current_price")),
        "eur_amount": _safe_float(preview.get("estimated_eur_total")),
        "asset_amount": _safe_float(preview.get("estimated_amount")),
        "filled_amount": _safe_float(bitvavo_response.get("filledAmount")),
        "filled_amount_quote": _safe_float(bitvavo_response.get("filledAmountQuote")),
        "fee_paid": _safe_float(bitvavo_response.get("feePaid")),
        "fee_currency": bitvavo_response.get("feeCurrency"),
        "bitvavo_order_id": bitvavo_response.get("orderId"),
        "operator_id": bitvavo_response.get("operatorId"),
        "raw_json": json.dumps(result, ensure_ascii=False),
    })

    return {
        "status": "ok",
        "preview_id": preview_id,
        "result": result,
    }
