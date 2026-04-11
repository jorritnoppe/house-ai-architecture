from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict


TRADE_STATE_DB_PATH = os.getenv(
    "TRADE_STATE_DB_PATH",
    "/home/jnoppe/house-agent/data/trade_state.db",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(TRADE_STATE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(TRADE_STATE_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_strategy_config (
                config_key TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


DEFAULT_STRATEGY_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "mode": "manual_only",
    "dry_run": True,
    "allowed_symbols": [],
    "blocked_symbols": ["ADA", "XRP"],
    "max_buy_eur_per_trade": 25.0,
    "max_sell_eur_per_trade": 50.0,
    "max_open_positions": 5,
    "stop_loss_pct": 8.0,
    "take_profit_pct": 15.0,
    "require_manual_approval_for_buys": True,
    "require_manual_approval_for_sells": True,
    "respect_locked_positions": True,
    "notes": "Safe scaffold only. No autonomous execution logic yet.",
}


class TradeStrategyState:
    def __init__(self) -> None:
        _init_db()

    def get_config(self) -> Dict[str, Any]:
        with _get_conn() as conn:
            row = conn.execute(
                """
                SELECT config_json, updated_at
                FROM trade_strategy_config
                WHERE config_key = ?
                """,
                ("strategy",),
            ).fetchone()

        if not row:
            return {
                "status": "ok",
                "config": DEFAULT_STRATEGY_CONFIG.copy(),
                "updated_at": None,
            }

        config = _json_loads(row["config_json"]) or DEFAULT_STRATEGY_CONFIG.copy()
        return {
            "status": "ok",
            "config": config,
            "updated_at": row["updated_at"],
        }

    def set_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_config()["config"]
        new_config = {**current, **updates}
        updated_at = _utc_now_iso()

        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO trade_strategy_config (config_key, config_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    config_json = excluded.config_json,
                    updated_at = excluded.updated_at
                """,
                ("strategy", _json_dumps(new_config), updated_at),
            )
            conn.commit()

        return {
            "status": "ok",
            "config": new_config,
            "updated_at": updated_at,
        }


trade_strategy_state = TradeStrategyState()
