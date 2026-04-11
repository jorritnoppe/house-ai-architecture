import logging
import math
import os
import threading
import time
from typing import Any

from influxdb_client import Point

from config import INFLUX_ORG
from extensions import write_api, query_api


logger = logging.getLogger(__name__)

LOXONE_HISTORY_BUCKET = os.getenv("LOXONE_HISTORY_BUCKET", "loxone_history")
LOXONE_HISTORY_MEASUREMENT = os.getenv("LOXONE_HISTORY_MEASUREMENT", "loxone_state")

TRACKED_STATE_INDEX: dict[str, dict[str, Any]] = {}

_LAST_LOGGED_STATE: dict[str, dict[str, Any]] = {}
_LAST_LOGGED_LOCK = threading.Lock()

UNCHANGED_HEARTBEAT_SECONDS = float(os.getenv("LOXONE_UNCHANGED_HEARTBEAT_SECONDS", "0"))
NUMERIC_EPSILON = float(os.getenv("LOXONE_NUMERIC_EPSILON", "0.0001"))


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

    if value.startswith("b'") and value.endswith("'"):
        value = value[2:-1]
    elif value.startswith('b"') and value.endswith('"'):
        value = value[2:-1]

    return value.lower()


def _safe_float(value: Any):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _values_equal(a: Any, b: Any) -> bool:
    if a is None and b is None:
        return True

    af = _safe_float(a)
    bf = _safe_float(b)

    if af is not None and bf is not None:
        if math.isnan(af) and math.isnan(bf):
            return True
        return abs(af - bf) <= NUMERIC_EPSILON

    return str(a) == str(b)


def rebuild_state_uuid_index():
    global TRACKED_STATE_INDEX

    from services.loxone_service import get_sensor_inventory

    inventory = get_sensor_inventory()
    items = inventory.get("items", [])

    index: dict[str, dict[str, Any]] = {}

    for item in items:
        states = item.get("states") or {}
        for state_key, state_uuid in states.items():
            norm = _normalize_uuid(state_uuid)
            if not norm:
                continue

            index[norm] = {
                "state_uuid": norm,
                "state_key": state_key,
                "control_uuid": item.get("uuid"),
                "control_name": item.get("name"),
                "room": item.get("room_name"),
                "domain": item.get("domain"),
                "sensor_type": item.get("sensor_type"),
                "type": item.get("type"),
                "role": item.get("role"),
                "tags": item.get("tags") or [],
            }

    TRACKED_STATE_INDEX = index
    logger.info("Loxone history state UUID index built with %s tracked states", len(TRACKED_STATE_INDEX))

    return {
        "status": "ok",
        "tracked_states": len(TRACKED_STATE_INDEX),
    }


def build_loxone_history_state_index():
    return rebuild_state_uuid_index()


def _should_log_state_change(state_uuid: str, value: Any) -> bool:
    now = time.time()

    with _LAST_LOGGED_LOCK:
        prev = _LAST_LOGGED_STATE.get(state_uuid)

        if prev is not None:
            prev_value = prev.get("value")
            prev_ts = float(prev.get("ts", 0))

            if _values_equal(prev_value, value):
                if UNCHANGED_HEARTBEAT_SECONDS <= 0:
                    return False
                if (now - prev_ts) < UNCHANGED_HEARTBEAT_SECONDS:
                    return False

        _LAST_LOGGED_STATE[state_uuid] = {
            "value": value,
            "ts": now,
        }
        return True


def log_loxone_state_change(state_uuid: str, value: Any):
    try:
        norm = _normalize_uuid(state_uuid)
        if not norm:
            return

        meta = TRACKED_STATE_INDEX.get(norm)
        if not meta:
            return

        if not _should_log_state_change(norm, value):
            return

        numeric_value = _safe_float(value)
        if numeric_value is None:
            return

        point = (
            Point(LOXONE_HISTORY_MEASUREMENT)
            .tag("state_uuid", norm)
            .tag("state_key", str(meta.get("state_key") or "unknown"))
            .tag("control_uuid", str(meta.get("control_uuid") or "unknown"))
            .tag("control_name", str(meta.get("control_name") or "unknown"))
            .tag("room", str(meta.get("room") or "unknown"))
            .tag("domain", str(meta.get("domain") or "unknown"))
            .tag("sensor_type", str(meta.get("sensor_type") or "unknown"))
            .field("value", numeric_value)
            .time(time.time_ns())
        )

        write_api.write(
            bucket=LOXONE_HISTORY_BUCKET,
            org=INFLUX_ORG,
            record=point,
        )

    except Exception:
        logger.exception(
            "Failed to write Loxone history point for state_uuid=%s value=%r",
            state_uuid,
            value,
        )


def get_recent_loxone_history(minutes: int = 30, room: str | None = None, limit: int = 500):
    try:
        minutes = int(minutes)
    except Exception:
        minutes = 30

    if minutes < 1:
        minutes = 1
    if minutes > 1440:
        minutes = 1440

    try:
        limit = int(limit)
    except Exception:
        limit = 500

    if limit < 1:
        limit = 1
    if limit > 5000:
        limit = 5000

    room_filter = ""
    if room:
        safe_room = str(room).replace('"', '\\"')
        room_filter = f'  |> filter(fn: (r) => r["room"] == "{safe_room}")\n'

    flux = f'''from(bucket: "{LOXONE_HISTORY_BUCKET}")
  |> range(start: -{minutes}m)
  |> filter(fn: (r) => r["_measurement"] == "{LOXONE_HISTORY_MEASUREMENT}")
  |> filter(fn: (r) => r["_field"] == "value")
{room_filter}  |> sort(columns: ["_time"], desc: false)
  |> limit(n: {limit})
'''

    try:
        tables = query_api.query(org=INFLUX_ORG, query=flux)
    except Exception as exc:
        logger.exception("Failed to query recent Loxone history")
        return {
            "status": "error",
            "message": f"Failed to query Loxone history: {exc}",
            "bucket": LOXONE_HISTORY_BUCKET,
            "measurement": LOXONE_HISTORY_MEASUREMENT,
            "minutes": minutes,
            "room": room,
        }

    items = []
    for table in tables:
        for record in table.records:
            items.append({
                "time": str(record.get_time()),
                "measurement": record.get_measurement(),
                "field": record.get_field(),
                "value": record.get_value(),
                "state_key": record.values.get("state_key"),
                "control_uuid": record.values.get("control_uuid"),
                "control_name": record.values.get("control_name"),
                "room": record.values.get("room"),
                "domain": record.values.get("domain"),
                "sensor_type": record.values.get("sensor_type"),
            })

    return {
        "status": "ok",
        "bucket": LOXONE_HISTORY_BUCKET,
        "measurement": LOXONE_HISTORY_MEASUREMENT,
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    }
