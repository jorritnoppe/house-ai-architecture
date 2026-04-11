from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


TRADE_STATE_DB_PATH = os.getenv(
    "TRADE_STATE_DB_PATH",
    "/opt/house-ai/data/trade_state.db",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _iso_after_seconds(seconds: int) -> str:
    return (_utc_now() + timedelta(seconds=int(seconds))).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str]) -> Any:
    if not value:
        return None
    return json.loads(value)


def _approval_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "token": row["token"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "expires_in_seconds": row["expires_in_seconds"],
        "auth_level": row["auth_level"],
        "approval_method": row["approval_method"],
        "question": row["question"],
        "room_id": row["room_id"],
        "requested_by": row["requested_by"],
        "action": _json_loads(row["action_json"]) or {},
        "approved_at": row["approved_at"],
        "approved_by": row["approved_by"],
        "approval_source": row["approval_source"],
        "consumed": bool(row["consumed"]),
        "consumed_at": row["consumed_at"],
    }


@contextmanager
def _connect():
    os.makedirs(os.path.dirname(TRADE_STATE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(TRADE_STATE_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_trade_state_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_previews (
                preview_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL,
                side TEXT,
                symbol TEXT,
                quote TEXT,
                market TEXT,
                eur_amount REAL,
                amount REAL,
                request_json TEXT NOT NULL,
                preview_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trade_previews_status ON trade_previews(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trade_previews_expires_at ON trade_previews(expires_at)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_approvals (
                token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                expires_in_seconds INTEGER NOT NULL,
                status TEXT NOT NULL,
                auth_level TEXT,
                approval_method TEXT,
                question TEXT,
                room_id TEXT,
                requested_by TEXT,
                approved_at TEXT,
                approved_by TEXT,
                approval_source TEXT,
                consumed INTEGER NOT NULL DEFAULT 0,
                consumed_at TEXT,
                action_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_approvals_status ON pending_approvals(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_approvals_expires_at ON pending_approvals(expires_at)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_position_locks (
                symbol TEXT PRIMARY KEY,
                locked INTEGER NOT NULL,
                reason TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_signal_states (
                source TEXT NOT NULL,
                signal TEXT NOT NULL,
                last_value INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (source, signal)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_approval_signal_states_updated_at ON approval_signal_states(updated_at)"
        )


class TradeStateStore:
    def __init__(self) -> None:
        init_trade_state_db()

    # ------------------------------------------------------------------
    # Approval signal state
    # ------------------------------------------------------------------

    def get_approval_signal_value(self, source: str, signal: str) -> bool:
        source = str(source or "").strip().lower()
        signal = str(signal or "").strip().lower()

        with _connect() as conn:
            row = conn.execute(
                """
                SELECT last_value
                FROM approval_signal_states
                WHERE source = ? AND signal = ?
                """,
                (source, signal),
            ).fetchone()

        if not row:
            return False
        return bool(int(row["last_value"] or 0))

    def set_approval_signal_value(self, source: str, signal: str, value: bool) -> Dict[str, Any]:
        source = str(source or "").strip().lower()
        signal = str(signal or "").strip().lower()
        now_iso = _utc_now_iso()
        value_int = 1 if bool(value) else 0

        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO approval_signal_states (source, signal, last_value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source, signal) DO UPDATE SET
                    last_value = excluded.last_value,
                    updated_at = excluded.updated_at
                """,
                (source, signal, value_int, now_iso),
            )

        return {
            "source": source,
            "signal": signal,
            "last_value": bool(value_int),
            "updated_at": now_iso,
        }

    def list_approval_signal_states(self) -> Dict[str, Any]:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT source, signal, last_value, updated_at
                FROM approval_signal_states
                ORDER BY source ASC, signal ASC
                """
            ).fetchall()

        sources: Dict[str, Dict[str, bool]] = {}
        raw_items: list[Dict[str, Any]] = []

        for row in rows:
            source = str(row["source"])
            signal = str(row["signal"])
            value = bool(int(row["last_value"] or 0))
            updated_at = row["updated_at"]

            sources.setdefault(source, {})
            sources[source][signal] = value

            raw_items.append(
                {
                    "source": source,
                    "signal": signal,
                    "last_value": value,
                    "updated_at": updated_at,
                }
            )

        return {
            "status": "ok",
            "generated_at": _utc_now_iso(),
            "sources": sources,
            "items": raw_items,
            "count": len(raw_items),
        }

    # ------------------------------------------------------------------
    # Position locks
    # ------------------------------------------------------------------

    def set_position_lock(
        self,
        *,
        symbol: str,
        locked: bool,
        reason: str | None = None,
    ) -> Dict[str, Any]:
        symbol = str(symbol or "").strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        updated_at = _utc_now_iso()

        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO trade_position_locks (
                    symbol, locked, reason, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    locked = excluded.locked,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (
                    symbol,
                    1 if bool(locked) else 0,
                    reason,
                    updated_at,
                ),
            )

        return {
            "symbol": symbol,
            "locked": bool(locked),
            "reason": reason,
            "updated_at": updated_at,
        }

    def get_position_lock(self, symbol: str) -> Dict[str, Any]:
        symbol = str(symbol or "").strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        with _connect() as conn:
            row = conn.execute(
                """
                SELECT symbol, locked, reason, updated_at
                FROM trade_position_locks
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()

        if not row:
            return {
                "symbol": symbol,
                "locked": False,
                "reason": None,
                "updated_at": None,
            }

        return {
            "symbol": row["symbol"],
            "locked": bool(row["locked"]),
            "reason": row["reason"],
            "updated_at": row["updated_at"],
        }

    def list_position_locks(self) -> Dict[str, Any]:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, locked, reason, updated_at
                FROM trade_position_locks
                ORDER BY symbol ASC
                """
            ).fetchall()

        items = []
        for row in rows:
            items.append(
                {
                    "symbol": row["symbol"],
                    "locked": bool(row["locked"]),
                    "reason": row["reason"],
                    "updated_at": row["updated_at"],
                }
            )

        return {
            "status": "ok",
            "count": len(items),
            "items": items,
            "generated_at": _utc_now_iso(),
        }

    # ------------------------------------------------------------------
    # Pending approvals
    # ------------------------------------------------------------------

    def cleanup_expired_approvals(self) -> int:
        now_iso = _utc_now_iso()
        with _connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM pending_approvals
                WHERE expires_at <= ?
                   OR consumed = 1
                   OR status = 'consumed'
                """,
                (now_iso,),
            )
            return int(cur.rowcount or 0)

    def create_pending_approval(
        self,
        *,
        token: str,
        auth_level: str,
        approval_method: str,
        action: Dict[str, Any],
        question: str | None = None,
        room_id: str | None = None,
        requested_by: str | None = None,
        expires_in_seconds: int = 90,
    ) -> Dict[str, Any]:
        created_at = _utc_now_iso()
        expires_at = _iso_after_seconds(expires_in_seconds)

        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO pending_approvals (
                    token, created_at, expires_at, expires_in_seconds, status,
                    auth_level, approval_method, question, room_id, requested_by,
                    approved_at, approved_by, approval_source,
                    consumed, consumed_at, action_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token,
                    created_at,
                    expires_at,
                    int(expires_in_seconds),
                    "pending",
                    auth_level,
                    approval_method,
                    question,
                    room_id,
                    requested_by,
                    None,
                    None,
                    None,
                    0,
                    None,
                    _json_dumps(action),
                ),
            )

        return self.get_pending_approval(token) or {}

    def get_pending_approval(self, token: str) -> Optional[Dict[str, Any]]:
        self.cleanup_expired_approvals()
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM pending_approvals
                WHERE token = ?
                """,
                (token,),
            ).fetchone()

        if not row:
            return None

        return _approval_row_to_dict(row)

    def get_latest_pending_approval(self, target: str | None = None) -> Optional[Dict[str, Any]]:
        self.cleanup_expired_approvals()
        with _connect() as conn:
            if target:
                row = conn.execute(
                    """
                    SELECT *
                    FROM pending_approvals
                    WHERE status = 'pending'
                      AND consumed = 0
                      AND json_extract(action_json, '$.target') = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (target,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT *
                    FROM pending_approvals
                    WHERE status = 'pending'
                      AND consumed = 0
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ).fetchone()

        if not row:
            return None

        return _approval_row_to_dict(row)

    def approve_pending_approval(
        self,
        *,
        token: str,
        approved_by: str | None = None,
        approval_source: str | None = None,
    ) -> Dict[str, Any]:
        self.cleanup_expired_approvals()
        now_iso = _utc_now_iso()

        with _connect() as conn:
            row = conn.execute(
                """
                SELECT token, status, consumed
                FROM pending_approvals
                WHERE token = ?
                """,
                (token,),
            ).fetchone()

            if not row:
                raise ValueError("Unknown or expired approval token")

            if int(row["consumed"] or 0) == 1:
                raise ValueError("Approval token already consumed")

            conn.execute(
                """
                UPDATE pending_approvals
                SET status = 'approved',
                    approved_at = ?,
                    approved_by = ?,
                    approval_source = ?
                WHERE token = ?
                """,
                (now_iso, approved_by, approval_source, token),
            )

        result = self.get_pending_approval(token)
        if not result:
            raise ValueError("Approval token disappeared after approval")
        return result

    def claim_pending_approval_for_execution(
        self,
        *,
        token: str,
        approved_by: str | None = None,
        approval_source: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        self.cleanup_expired_approvals()
        now_iso = _utc_now_iso()

        with _connect() as conn:
            cur = conn.execute(
                """
                UPDATE pending_approvals
                SET status = 'executing',
                    approved_at = COALESCE(approved_at, ?),
                    approved_by = COALESCE(approved_by, ?),
                    approval_source = COALESCE(approval_source, ?)
                WHERE token = ?
                  AND status = 'pending'
                  AND consumed = 0
                """,
                (now_iso, approved_by, approval_source, token),
            )

            if int(cur.rowcount or 0) != 1:
                return None

        return self.get_pending_approval(token)

    def revert_approval_to_pending(self, token: str) -> Dict[str, Any]:
        self.cleanup_expired_approvals()

        with _connect() as conn:
            row = conn.execute(
                """
                SELECT token, status, consumed
                FROM pending_approvals
                WHERE token = ?
                """,
                (token,),
            ).fetchone()

            if not row:
                raise ValueError("Unknown or expired approval token")

            if int(row["consumed"] or 0) == 1:
                raise ValueError("Approval token already consumed")

            conn.execute(
                """
                UPDATE pending_approvals
                SET status = 'pending'
                WHERE token = ?
                """,
                (token,),
            )

        result = self.get_pending_approval(token)
        if not result:
            raise ValueError("Approval token disappeared after revert")
        return result

    def consume_pending_approval(self, token: str) -> Dict[str, Any]:
        self.cleanup_expired_approvals()
        now_iso = _utc_now_iso()

        with _connect() as conn:
            row = conn.execute(
                """
                SELECT token, status, consumed
                FROM pending_approvals
                WHERE token = ?
                """,
                (token,),
            ).fetchone()

            if not row:
                raise ValueError("Unknown or expired approval token")

            if str(row["status"]) not in {"approved", "executing"}:
                raise ValueError("Approval token is not approved or executing")

            if int(row["consumed"] or 0) == 1:
                return {
                    "token": token,
                    "status": "consumed",
                    "consumed": True,
                    "consumed_at": row["consumed_at"] if "consumed_at" in row.keys() else now_iso,
                }

            conn.execute(
                """
                UPDATE pending_approvals
                SET consumed = 1,
                    consumed_at = ?,
                    status = 'consumed'
                WHERE token = ?
                """,
                (now_iso, token),
            )

        result = self.get_pending_approval(token)
        if result is not None:
            return result

        return {
            "token": token,
            "status": "consumed",
            "consumed": True,
            "consumed_at": now_iso,
        }

    def list_pending_approvals(self) -> Dict[str, Any]:
        self.cleanup_expired_approvals()
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM pending_approvals
                WHERE status = 'pending' AND consumed = 0
                ORDER BY created_at DESC
                """
            ).fetchall()

        items = []
        for row in rows:
            items.append(_approval_row_to_dict(row))

        return {
            "status": "ok",
            "count": len(items),
            "items": items,
            "generated_at": _utc_now_iso(),
        }

    # ------------------------------------------------------------------
    # Trade previews
    # ------------------------------------------------------------------

    def cleanup_expired_previews(self) -> int:
        now_iso = _utc_now_iso()
        with _connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM trade_previews
                WHERE expires_at <= ?
                   OR status IN ('consumed', 'expired')
                """,
                (now_iso,),
            )
            return int(cur.rowcount or 0)

    def create_preview(
        self,
        *,
        preview_id: str,
        ttl_seconds: int,
        request_payload: Dict[str, Any],
        preview_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        created_at = _utc_now_iso()
        expires_at = _iso_after_seconds(ttl_seconds)

        side = str(preview_payload.get("side") or request_payload.get("side") or "")
        symbol = str(preview_payload.get("base") or request_payload.get("symbol") or "")
        quote = str(preview_payload.get("quote") or request_payload.get("quote") or "EUR")
        market = str(preview_payload.get("market") or request_payload.get("market") or "")
        eur_amount = preview_payload.get("estimated_eur_total", request_payload.get("eur_amount"))
        amount = preview_payload.get("estimated_amount", request_payload.get("amount"))

        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO trade_previews (
                    preview_id, created_at, expires_at, status,
                    side, symbol, quote, market, eur_amount, amount,
                    request_json, preview_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preview_id,
                    created_at,
                    expires_at,
                    "pending",
                    side,
                    symbol,
                    quote,
                    market,
                    eur_amount,
                    amount,
                    _json_dumps(request_payload),
                    _json_dumps(preview_payload),
                ),
            )

        return self.get_preview(preview_id) or {}

    def get_preview(self, preview_id: str) -> Optional[Dict[str, Any]]:
        self.cleanup_expired_previews()
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM trade_previews
                WHERE preview_id = ?
                """,
                (preview_id,),
            ).fetchone()

        if not row:
            return None

        return {
            "preview_id": row["preview_id"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "status": row["status"],
            "side": row["side"],
            "symbol": row["symbol"],
            "quote": row["quote"],
            "market": row["market"],
            "eur_amount": row["eur_amount"],
            "amount": row["amount"],
            "request": _json_loads(row["request_json"]) or {},
            "preview": _json_loads(row["preview_json"]) or {},
        }

    def mark_preview_consumed(self, preview_id: str) -> None:
        with _connect() as conn:
            conn.execute(
                """
                UPDATE trade_previews
                SET status = 'consumed'
                WHERE preview_id = ?
                """,
                (preview_id,),
            )

    def list_recent_previews(self, limit: int = 20) -> Dict[str, Any]:
        self.cleanup_expired_previews()
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM trade_previews
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

        items = []
        for row in rows:
            items.append(
                {
                    "preview_id": row["preview_id"],
                    "created_at": row["created_at"],
                    "expires_at": row["expires_at"],
                    "status": row["status"],
                    "side": row["side"],
                    "symbol": row["symbol"],
                    "quote": row["quote"],
                    "market": row["market"],
                    "eur_amount": row["eur_amount"],
                    "amount": row["amount"],
                    "request": _json_loads(row["request_json"]) or {},
                    "preview": _json_loads(row["preview_json"]) or {},
                }
            )

        return {
            "status": "ok",
            "count": len(items),
            "items": items,
            "generated_at": _utc_now_iso(),
        }


trade_state_store = TradeStateStore()
