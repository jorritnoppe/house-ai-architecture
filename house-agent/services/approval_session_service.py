from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Dict, Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


class ApprovalSessionService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _cleanup(self) -> None:
        now = _utc_now()
        expired = []

        for approver, item in self._sessions.items():
            expires_at = item.get("expires_at")
            revoked_at = item.get("revoked_at")

            if revoked_at:
                expired.append(approver)
                continue

            if expires_at:
                try:
                    if datetime.fromisoformat(expires_at) <= now:
                        expired.append(approver)
                except Exception:
                    expired.append(approver)

        for approver in expired:
            self._sessions.pop(approver, None)

    def activate(
        self,
        approver: str,
        source: str,
        duration_seconds: int = 7200,
    ) -> Dict[str, Any]:
        approver = str(approver or "").strip().lower()
        source = str(source or "").strip()
        if not approver:
            raise ValueError("Missing approver")
        if not source:
            raise ValueError("Missing source")

        with self._lock:
            self._cleanup()
            now = _utc_now()
            expires_at = now + timedelta(seconds=int(duration_seconds))

            item = {
                "approver": approver,
                "source": source,
                "active": True,
                "started_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "revoked_at": None,
            }
            self._sessions[approver] = item
            return deepcopy(item)

    def revoke(self, approver: str, source: str | None = None) -> Dict[str, Any]:
        approver = str(approver or "").strip().lower()
        if not approver:
            raise ValueError("Missing approver")

        with self._lock:
            self._cleanup()
            current = self._sessions.get(approver)
            if not current:
                return {
                    "approver": approver,
                    "source": source,
                    "active": False,
                    "revoked": False,
                    "reason": "No active session found.",
                }

            current["revoked_at"] = _utc_now_iso()
            current["active"] = False
            result = deepcopy(current)
            self._sessions.pop(approver, None)
            return result

    def is_active(self, approver: str) -> bool:
        approver = str(approver or "").strip().lower()
        if not approver:
            return False

        with self._lock:
            self._cleanup()
            item = self._sessions.get(approver)
            return bool(item and item.get("active") is True)

    def get_active_session(self, approver: str) -> Optional[Dict[str, Any]]:
        approver = str(approver or "").strip().lower()
        if not approver:
            return None

        with self._lock:
            self._cleanup()
            item = self._sessions.get(approver)
            return deepcopy(item) if item else None

    def list_active(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup()
            items = list(deepcopy(self._sessions).values())

        return {
            "status": "ok",
            "generated_at": _utc_now_iso(),
            "count": len(items),
            "items": items,
        }


_session_singleton: ApprovalSessionService | None = None
_session_lock = RLock()


def get_approval_session_service() -> ApprovalSessionService:
    global _session_singleton
    with _session_lock:
        if _session_singleton is None:
            _session_singleton = ApprovalSessionService()
        return _session_singleton
