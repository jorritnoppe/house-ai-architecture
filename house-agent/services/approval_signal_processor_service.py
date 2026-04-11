# services/approval_signal_processor_service.py
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict

from services.approval_session_service import get_approval_session_service
from services.pending_approval_service import get_pending_approval_service
from services.approved_action_executor_service import execute_approved_action
from services.trade_state_store import trade_state_store


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


APPROVAL_INPUT_MAP = {
    "masterbedroom_nfc": {
        "approve": "approve_active_request",
        "jorrit": "jorrit_on",
        "jorritoff": "jorrit_off",
    },
    "masterbedroom_nfc_access_control": {
        "approve": "approve_active_request",
        "jorrit": "jorrit_on",
        "jorritoff": "jorrit_off",
    },
    "kitchenroom_nfc": {
        "approve": "approve_active_request",
        "jorrit": "jorrit_on",
        "jorritoff": "jorrit_off",
    },
    "kitchenroom_nfc_access_control": {
        "approve": "approve_active_request",
        "jorrit": "jorrit_on",
        "jorritoff": "jorrit_off",
    },
    "entranceroom_nfc": {
        "approve": "approve_active_request",
        "jorrit": "jorrit_on",
        "jorritoff": "jorrit_off",
    },
    "entranceroom_nfc_access_control": {
        "approve": "approve_active_request",
        "jorrit": "jorrit_on",
        "jorritoff": "jorrit_off",
    },
}


class ApprovalSignalProcessorService:
    def __init__(self) -> None:
        self._lock = RLock()

    def _normalize_source(self, source: str) -> str:
        source = str(source or "").strip().lower()
        if not source:
            raise ValueError("Missing source")
        if source not in APPROVAL_INPUT_MAP:
            raise ValueError(f"Unknown approval source: {source}")
        return source

    def _normalize_signal(self, source: str, signal: str) -> str:
        signal = str(signal or "").strip().lower()
        mapped = APPROVAL_INPUT_MAP[source].get(signal)
        if not mapped:
            raise ValueError(f"Unknown signal for {source}: {signal}")
        return mapped

    def _get_last_value(self, source: str, signal: str) -> bool:
        return trade_state_store.get_approval_signal_value(source, signal)

    def _set_last_value(self, source: str, signal: str, value: bool) -> Dict[str, Any]:
        return trade_state_store.set_approval_signal_value(source, signal, value)

    def list_states(self) -> Dict[str, Any]:
        return trade_state_store.list_approval_signal_states()

    def process_signal(
        self,
        source: str,
        signal: str,
        value: Any,
    ) -> Dict[str, Any]:
        source = self._normalize_source(source)
        normalized_signal = self._normalize_signal(source, signal)
        current_value = bool(value)

        with self._lock:
            previous_value = self._get_last_value(source, normalized_signal)
            state_row = self._set_last_value(source, normalized_signal, current_value)

        rising_edge = (not previous_value) and current_value

        result: Dict[str, Any] = {
            "status": "ok",
            "source": source,
            "signal": signal,
            "normalized_signal": normalized_signal,
            "value": current_value,
            "previous_value": previous_value,
            "rising_edge": rising_edge,
            "processed_at": _utc_now_iso(),
            "effect": None,
            "state": state_row,
        }

        if not rising_edge:
            result["effect"] = "no_edge_no_action"
            return result

        if normalized_signal == "approve_active_request":
            pending_service = get_pending_approval_service()
            latest = pending_service.get_latest_pending()

            if not latest:
                result["effect"] = "approve_requested_but_no_pending_action"
                return result

            token = str(latest.get("token") or "").strip()
            if not token:
                result["effect"] = "pending_action_missing_token"
                return result

            claimed = pending_service.claim_for_execution(
                token=token,
                approved_by=source,
                approval_source=source,
            )

            if not claimed:
                result["effect"] = "approval_already_claimed_by_other_worker"
                return result

            executor_result = execute_approved_action(token)

            if executor_result.get("status") == "ok":
                consumed = pending_service.consume(token)
                result["effect"] = "approved_and_executed_latest"
                result["approval"] = consumed
                result["executor_result"] = executor_result
                return result

            reverted = pending_service.revert_to_pending(token)
            result["effect"] = "approval_claimed_but_execution_failed"
            result["approval"] = reverted
            result["executor_result"] = executor_result
            return result

        if normalized_signal == "jorrit_on":
            session = get_approval_session_service().activate(
                approver="jorrit",
                source=source,
                duration_seconds=7200,
            )
            result["effect"] = "jorrit_session_started"
            result["session"] = session
            return result

        if normalized_signal == "jorrit_off":
            session = get_approval_session_service().revoke(
                approver="jorrit",
                source=source,
            )
            result["effect"] = "jorrit_session_revoked"
            result["session"] = session
            return result

        result["effect"] = "unknown_edge"
        return result


_signal_singleton: ApprovalSignalProcessorService | None = None
_signal_lock = RLock()


def get_approval_signal_processor_service() -> ApprovalSignalProcessorService:
    global _signal_singleton
    with _signal_lock:
        if _signal_singleton is None:
            _signal_singleton = ApprovalSignalProcessorService()
        return _signal_singleton
