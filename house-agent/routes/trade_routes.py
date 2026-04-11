from __future__ import annotations

from flask import Blueprint, jsonify, request, render_template

from services.pending_approval_service import get_pending_approval_service
from services.trade_audit_service import get_recent_trade_audit
from services.trade_state_store import trade_state_store
from services.trade_strategy_state import trade_strategy_state
from services.trade_summary_service import build_holdings_summary
from services.trade_service import (
    confirm_trade,
    create_preview,
    get_positions,
    get_trade_config,
)
from services.bitvavo_trade_service import bitvavo_trade_service


trade_bp = Blueprint("trade", __name__)


@trade_bp.get("/api/trade/config")
def trade_config():
    try:
        return jsonify(get_trade_config())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/positions")
def trade_positions():
    try:
        return jsonify(get_positions())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/markets")
def trade_markets():
    try:
        markets = bitvavo_trade_service.get_markets()
        rows = (markets or {}).get("markets", []) if isinstance(markets, dict) else []

        items = []
        seen = set()

        for row in rows:
            if not isinstance(row, dict):
                continue

            market = str(row.get("market") or "").strip().upper()
            base = str(row.get("base") or "").strip().upper()
            quote = str(row.get("quote") or "").strip().upper()
            status = str(row.get("status") or "").strip().lower()

            if not market or not base:
                continue
            if quote != "EUR":
                continue
            if status not in {"trading", "auction"}:
                continue
            if base in seen:
                continue

            seen.add(base)
            items.append({
                "symbol": base,
                "market": market,
                "quote": quote,
                "status": status,
            })

        items.sort(key=lambda x: x["symbol"])

        return jsonify({
            "status": "ok",
            "count": len(items),
            "items": items,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/holdings")
def trade_holdings():
    try:
        balance = bitvavo_trade_service.get_balance()
        markets = bitvavo_trade_service.get_marketsxml()
        lock_result = trade_state_store.list_position_locks()

        assets = balance.get("assets", []) if isinstance(balance, dict) else []
        market_rows = markets
        lock_rows = lock_result.get("items", []) if isinstance(lock_result, dict) else []

        result = build_holdings_summary(
            balances=assets,
            market_rows=market_rows,
            lock_rows=lock_rows,
        )

        result["sources"] = {
            "balance_status": balance.get("status") if isinstance(balance, dict) else "unknown",
            "markets_status": "ok",
            "locks_status": lock_result.get("status") if isinstance(lock_result, dict) else "unknown",
        }
        return jsonify(result)
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/audit/recent")
def trade_audit_recent():
    try:
        limit = int(request.args.get("limit", "20"))
        return jsonify(get_recent_trade_audit(limit=limit))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/strategy/config")
def trade_strategy_config_get():
    try:
        return jsonify(trade_strategy_state.get_config())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.post("/api/trade/strategy/config")
def trade_strategy_config_set():
    try:
        payload = request.get_json(silent=True) or {}

        updates = {
            "enabled": bool(payload.get("enabled", False)),
            "mode": str(payload.get("mode", "manual_only")).strip(),
            "dry_run": bool(payload.get("dry_run", True)),
            "allowed_symbols": payload.get("allowed_symbols", []),
            "blocked_symbols": payload.get("blocked_symbols", []),
            "max_buy_eur_per_trade": float(payload.get("max_buy_eur_per_trade", 25.0)),
            "max_sell_eur_per_trade": float(payload.get("max_sell_eur_per_trade", 50.0)),
            "max_open_positions": int(payload.get("max_open_positions", 5)),
            "stop_loss_pct": float(payload.get("stop_loss_pct", 8.0)),
            "take_profit_pct": float(payload.get("take_profit_pct", 15.0)),
            "require_manual_approval_for_buys": bool(payload.get("require_manual_approval_for_buys", True)),
            "require_manual_approval_for_sells": bool(payload.get("require_manual_approval_for_sells", True)),
            "respect_locked_positions": bool(payload.get("respect_locked_positions", True)),
            "notes": str(payload.get("notes", "")).strip(),
        }

        return jsonify(trade_strategy_state.set_config(updates))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@trade_bp.get("/api/trade/dashboard")
def trade_dashboard():
    try:
        balance = bitvavo_trade_service.get_balance()
        markets = bitvavo_trade_service.get_marketsxml()
        lock_result = trade_state_store.list_position_locks()
        previews = trade_state_store.list_recent_previews(limit=10)
        audit = get_recent_trade_audit(limit=10)
        strategy = trade_strategy_state.get_config()

        assets = balance.get("assets", []) if isinstance(balance, dict) else []
        lock_rows = lock_result.get("items", []) if isinstance(lock_result, dict) else []

        holdings_result = build_holdings_summary(
            balances=assets,
            market_rows=markets,
            lock_rows=lock_rows,
        )

        holdings = holdings_result.get("holdings", []) or []
        total_value = float((holdings_result.get("totals") or {}).get("total_eur_value") or 0.0)

        locked_value = round(
            sum(float(x.get("eur_value") or 0.0) for x in holdings if x.get("locked")),
            2,
        )
        unlocked_value = round(total_value - locked_value, 2)

        zero_value_items = [
            {
                "symbol": x.get("symbol"),
                "amount": x.get("amount"),
                "market": x.get("market"),
                "locked": x.get("locked"),
            }
            for x in holdings
            if float(x.get("eur_value") or 0.0) == 0.0
        ]

        top_holdings = holdings[:8]

        return jsonify({
            "status": "ok",
            "summary": {
                "total_wallet_value_eur": round(total_value, 2),
                "locked_value_eur": locked_value,
                "unlocked_value_eur": unlocked_value,
                "asset_count": len(holdings),
                "locked_asset_count": len([x for x in holdings if x.get("locked")]),
                "zero_value_asset_count": len(zero_value_items),
            },
            "top_holdings": top_holdings,
            "zero_value_items": zero_value_items,
            "recent_previews": previews,
            "recent_audit": audit,
            "strategy": strategy,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/ui/crypto")
def trade_ui_crypto():
    return render_template("crypto.html")


@trade_bp.post("/api/trade/preview")
def trade_preview():
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(create_preview(payload))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@trade_bp.post("/api/trade/confirm")
def trade_confirm():
    try:
        payload = request.get_json(silent=True) or {}
        preview_id = str(payload.get("preview_id", "")).strip()
        if not preview_id:
            return jsonify({"status": "error", "error": "preview_id is required"}), 400
        return jsonify(confirm_trade(preview_id))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@trade_bp.post("/api/trade/execute-approved")
def trade_execute_approved():
    try:
        payload = request.get_json(silent=True) or {}
        preview_id = str(payload.get("preview_id", "")).strip()
        if not preview_id:
            return jsonify({"status": "error", "error": "preview_id is required"}), 400
        return jsonify(confirm_trade(preview_id))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@trade_bp.post("/api/trade/request-approval")
def trade_request_approval():
    try:
        payload = request.get_json(silent=True) or {}
        preview_id = str(payload.get("preview_id", "")).strip()

        if not preview_id:
            return jsonify({"status": "error", "error": "preview_id is required"}), 400

        preview_record = trade_state_store.get_preview(preview_id)
        if not preview_record:
            return jsonify({"status": "error", "error": "preview_id not found or expired"}), 404

        preview = preview_record.get("preview") or {}
        side = str(preview.get("side") or "").strip().lower()
        symbol = str(preview.get("base") or "").strip().upper()
        eur_value = preview.get("estimated_eur_total")

        approval = get_pending_approval_service().create_request(
            action={
                "type": "route",
                "method": "POST",
                "target": "/api/trade/execute-approved",
                "params": {
                    "preview_id": preview_id,
                },
            },
            auth_level="approval_required",
            approval_method="future_loxone_nfc_or_keypad",
            question=f"Approve {side} crypto trade for {symbol} preview {preview_id} value {eur_value} EUR?",
            room_id=payload.get("room_id"),
            requested_by=payload.get("requested_by", "trade_ui"),
            expires_in_seconds=payload.get("expires_in_seconds", 90),
        )

        return jsonify({
            "status": "ok",
            "approval": approval,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@trade_bp.get("/api/trade/previews")
def trade_previews():
    try:
        limit = int(request.args.get("limit", "20"))
        return jsonify(trade_state_store.list_recent_previews(limit=limit))
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/locks")
def trade_locks():
    try:
        return jsonify(trade_state_store.list_position_locks())
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@trade_bp.get("/api/trade/lock/<symbol>")
def trade_lock_get(symbol: str):
    try:
        return jsonify({
            "status": "ok",
            "item": trade_state_store.get_position_lock(symbol),
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400


@trade_bp.post("/api/trade/lock")
def trade_lock_set():
    try:
        payload = request.get_json(silent=True) or {}
        symbol = str(payload.get("symbol") or "").strip().upper()
        locked = bool(payload.get("locked", True))
        reason = str(payload.get("reason") or "").strip()

        if not symbol:
            return jsonify({"status": "error", "error": "missing symbol"}), 400

        result = trade_state_store.set_position_lock(
            symbol=symbol,
            locked=locked,
            reason=reason,
        )
        return jsonify({
            "status": "ok",
            "item": result,
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400
