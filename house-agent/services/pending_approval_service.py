# services/pending_approval_service.py
from __future__ import annotations

import secrets
from threading import RLock
from typing import Any, Dict, Optional

from services.trade_state_store import trade_state_store


class PendingApprovalService:
    def __init__(self, default_expiry_seconds: int = 90) -> None:
        self.default_expiry_seconds = int(default_expiry_seconds)

    def create_request(
        self,
        action: Dict[str, Any],
        auth_level: str,
        approval_method: str,
        question: str | None = None,
        room_id: str | None = None,
        requested_by: str | None = None,
        expires_in_seconds: int | None = None,
    ) -> Dict[str, Any]:
        token = secrets.token_urlsafe(16)
        ttl = int(expires_in_seconds or self.default_expiry_seconds)

        return trade_state_store.create_pending_approval(
            token=token,
            auth_level=auth_level,
            approval_method=approval_method,
            action=action,
            question=question,
            room_id=room_id,
            requested_by=requested_by,
            expires_in_seconds=ttl,
        )

    def approve(
        self,
        token: str,
        approved_by: str | None = None,
        approval_source: str | None = None,
    ) -> Dict[str, Any]:
        return trade_state_store.approve_pending_approval(
            token=token,
            approved_by=approved_by,
            approval_source=approval_source,
        )

    def get(self, token: str) -> Optional[Dict[str, Any]]:
        return trade_state_store.get_pending_approval(token)

    def consume(self, token: str) -> Dict[str, Any]:
        return trade_state_store.consume_pending_approval(token)

    def list_pending(self) -> Dict[str, Any]:
        return trade_state_store.list_pending_approvals()

    def get_latest_pending(self, target: str | None = None) -> Optional[Dict[str, Any]]:
        return trade_state_store.get_latest_pending_approval(target=target)

    def claim_for_execution(
        self,
        *,
        token: str,
        approved_by: str | None = None,
        approval_source: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        return trade_state_store.claim_pending_approval_for_execution(
            token=token,
            approved_by=approved_by,
            approval_source=approval_source,
        )

    def revert_to_pending(self, token: str) -> Dict[str, Any]:
        return trade_state_store.revert_approval_to_pending(token)


_pending_singleton: PendingApprovalService | None = None
_pending_lock = RLock()


def get_pending_approval_service() -> PendingApprovalService:
    global _pending_singleton
    with _pending_lock:
        if _pending_singleton is None:
            _pending_singleton = PendingApprovalService()
        return _pending_singleton
