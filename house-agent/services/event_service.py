# services/event_service.py

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def publish_event(event_name: str, payload: dict | None = None):
    event = {
        "event": event_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    logger.info("EVENT %s", event)
    return event
