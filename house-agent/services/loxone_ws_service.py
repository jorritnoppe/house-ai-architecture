import asyncio
import logging
import os
import threading
import time
from typing import Any

from services.loxone_history_service import log_loxone_state_change
from config import LOXONE_HOST, LOXONE_USER, LOXONE_PASSWORD
from services.approval_signal_bridge_service import process_ws_uuid_update


logger = logging.getLogger(__name__)

BASE_HTTP = f"http://{LOXONE_HOST}"
WS_URL = f"ws://{LOXONE_HOST}/ws/rfc6455"

# live cache: state uuid -> decoded value
LOXONE_STATE_CACHE: dict[str, Any] = {}
LOXONE_LAST_SEEN_TS: float | None = None

_WS_THREAD = None
_WS_LOOP = None
_WS_CLIENT = None
_WS_STARTED = False

try:
    from loxwebsocket import LoxWs
except Exception:
    LoxWs = None


def _normalize_uuid(value):
    if value is None:
        return None

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            value = str(value)
    else:
        value = str(value)

    value = value.strip()

    # fix broken "b'...'" stringified bytes values
    if value.startswith("b'") and value.endswith("'"):
        value = value[2:-1]
    elif value.startswith('b"') and value.endswith('"'):
        value = value[2:-1]

    return value.lower()


async def _on_value_update(data, message_type: int):
    global LOXONE_LAST_SEEN_TS

    LOXONE_LAST_SEEN_TS = time.time()

    try:
        if isinstance(data, dict):
            for k, v in data.items():
                norm = _normalize_uuid(k)

                if norm:
                    LOXONE_STATE_CACHE[norm] = v
                    log_loxone_state_change(norm, v)
                    process_ws_uuid_update(norm, v)
            return

        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue

                uuid = item.get("uuid") or item.get("id")
                value = item.get("value")

                norm = _normalize_uuid(uuid)



                if norm:
                    LOXONE_STATE_CACHE[norm] = value
                    log_loxone_state_change(norm, value)
                    process_ws_uuid_update(norm, value)

            return

        logger.debug("Unhandled Loxone WS callback payload type: %s", type(data).__name__)
    except Exception:
        logger.exception("Error while processing Loxone websocket update")


async def _ws_main():
    global _WS_CLIENT, LOXONE_LAST_SEEN_TS

    if LoxWs is None:
        logger.error("loxwebsocket package not installed. Run: pip install loxwebsocket")
        return

    logger.info("Starting Loxone websocket client for host %s", LOXONE_HOST)

    ws = LoxWs()
    _WS_CLIENT = ws

    try:
        ws.add_message_callback(_on_value_update, message_types=[2])

        await ws.connect(
            user=LOXONE_USER,
            password=LOXONE_PASSWORD,
            loxone_url=BASE_HTTP,
            receive_updates=True,
            max_reconnect_attempts=0,
        )

        LOXONE_LAST_SEEN_TS = time.time()
        logger.info("Loxone websocket connected successfully")

        while True:
            await asyncio.sleep(30)

    except Exception as exc:
        logger.exception("Loxone websocket loop error: %s", exc)

    finally:
        try:
            await ws.stop()
        except Exception:
            pass


def _thread_main():
    global _WS_LOOP
    _WS_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(_WS_LOOP)
    _WS_LOOP.run_until_complete(_ws_main())


def _should_start_ws_in_this_process() -> bool:
    enabled = os.environ.get("HOUSE_AGENT_RUN_LOXONE_WS", "0").strip().lower()
    return enabled in ("1", "true", "yes", "on")


def start_loxone_ws_background():
    global _WS_THREAD, _WS_STARTED

    if _WS_STARTED:
        logger.info("Loxone websocket background already started")
        return

    if not _should_start_ws_in_this_process():
        logger.info("Skipping Loxone websocket startup in this process")
        return

    _WS_STARTED = True
    LOXONE_STATE_CACHE.clear()

    _WS_THREAD = threading.Thread(
        target=_thread_main,
        name="loxone-ws",
        daemon=True,
    )
    _WS_THREAD.start()

    logger.info("Started Loxone websocket background thread")


def get_cached_loxone_value(state_uuid: str):
    normalized = _normalize_uuid(state_uuid)
    if not normalized:
        return None

    return LOXONE_STATE_CACHE.get(normalized)


def get_loxone_ws_status():
    return {
        "status": "ok",
        "host": LOXONE_HOST,
        "ws_url": WS_URL,
        "cached_values": len(LOXONE_STATE_CACHE),
        "last_seen_ts": LOXONE_LAST_SEEN_TS,
        "client_loaded": True,
        "ws_enabled_in_this_process": _should_start_ws_in_this_process(),
    }


def get_loxone_ws_cache_sample(limit: int = 50, contains: str | None = None):
    try:
        limit = int(limit)
    except Exception:
        limit = 50

    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    contains_norm = _normalize_uuid(contains) if contains else None

    items = []
    for raw_uuid, value in LOXONE_STATE_CACHE.items():
        uuid = _normalize_uuid(raw_uuid)
        if not uuid:
            continue

        if contains_norm and contains_norm not in uuid:
            continue

        items.append({
            "uuid": uuid,
            "value": value,
        })

        if len(items) >= limit:
            break

    return {
        "status": "ok",
        "cached_values": len(LOXONE_STATE_CACHE),
        "count": len(items),
        "contains": contains_norm,
        "items": items,
    }
