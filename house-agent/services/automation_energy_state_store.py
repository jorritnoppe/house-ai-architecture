from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict


AUTOMATION_STATE_DB_PATH = os.getenv(
    "AUTOMATION_STATE_DB_PATH",
    "/home/jnoppe/house-agent/data/automation_state.db",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    os.makedirs(os.path.dirname(AUTOMATION_STATE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(AUTOMATION_STATE_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_automation_state_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_energy_state (
                state_key TEXT PRIMARY KEY,
                current_level TEXT NOT NULL,
                stable_since_ts REAL,
                last_state_change_ts REAL,
                cooldown_until_ts REAL,
                updated_at TEXT NOT NULL
            )
            """
        )


class AutomationEnergyStateStore:
    def __init__(self) -> None:
        init_automation_state_db()

    def get_state(self) -> Dict[str, Any]:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT state_key, current_level, stable_since_ts, last_state_change_ts, cooldown_until_ts, updated_at
                FROM automation_energy_state
                WHERE state_key = ?
                """,
                ("excess_energy",),
            ).fetchone()

        if not row:
            return {
                "state_key": "excess_energy",
                "current_level": "none",
                "stable_since_ts": None,
                "last_state_change_ts": None,
                "cooldown_until_ts": None,
                "updated_at": None,
            }

        return {
            "state_key": row["state_key"],
            "current_level": row["current_level"],
            "stable_since_ts": row["stable_since_ts"],
            "last_state_change_ts": row["last_state_change_ts"],
            "cooldown_until_ts": row["cooldown_until_ts"],
            "updated_at": row["updated_at"],
        }

    def set_state(
        self,
        *,
        current_level: str,
        stable_since_ts: float | None,
        last_state_change_ts: float | None,
        cooldown_until_ts: float | None,
    ) -> Dict[str, Any]:
        updated_at = _utc_now_iso()

        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO automation_energy_state (
                    state_key,
                    current_level,
                    stable_since_ts,
                    last_state_change_ts,
                    cooldown_until_ts,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    current_level = excluded.current_level,
                    stable_since_ts = excluded.stable_since_ts,
                    last_state_change_ts = excluded.last_state_change_ts,
                    cooldown_until_ts = excluded.cooldown_until_ts,
                    updated_at = excluded.updated_at
                """,
                (
                    "excess_energy",
                    current_level,
                    stable_since_ts,
                    last_state_change_ts,
                    cooldown_until_ts,
                    updated_at,
                ),
            )

        return self.get_state()


automation_energy_state_store = AutomationEnergyStateStore()
