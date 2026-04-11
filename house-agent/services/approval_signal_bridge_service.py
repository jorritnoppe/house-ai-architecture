from __future__ import annotations

import logging
from typing import Any

from services.approval_signal_processor_service import get_approval_signal_processor_service

logger = logging.getLogger(__name__)

APPROVAL_SIGNAL_UUID_MAP = {
    "2073f2a7-03d6-f7f1-05ff5d6294eb1538": {
        "source": "masterbedroom_nfc",
        "signal": "approve",
        "name": "masterbedroom approve pulse",
    },
}


def _to_bool(value: Any) -> bool:
    try:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return float(value) != 0.0
        text = str(value).strip().lower()
        return text in {"1", "1.0", "true", "on", "yes"}
    except Exception:
        return False


def process_ws_uuid_update(state_uuid: str, value: Any) -> None:
    state_uuid = str(state_uuid or "").strip().lower()
    mapping = APPROVAL_SIGNAL_UUID_MAP.get(state_uuid)
    if not mapping:
        return

    current = _to_bool(value)

    try:
        result = get_approval_signal_processor_service().process_signal(
            source=mapping["source"],
            signal=mapping["signal"],
            value=1 if current else 0,
        )

        if current:
            logger.warning(
                "APPROVAL_WS_BRIDGE fired uuid=%s name=%s result=%r",
                state_uuid,
                mapping.get("name"),
                result,
            )
        else:
            logger.warning(
                "APPROVAL_WS_BRIDGE falling-edge uuid=%s name=%s result=%r",
                state_uuid,
                mapping.get("name"),
                result,
            )

    except Exception:
        logger.exception(
            "APPROVAL_WS_BRIDGE failed uuid=%s name=%s value=%r",
            state_uuid,
            mapping.get("name"),
            value,
        )
