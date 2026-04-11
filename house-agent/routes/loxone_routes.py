from flask import Blueprint, jsonify, request

from services.loxone_service import (
    get_room_climate_summary,
    get_live_values_by_room,
)

from services.loxone_ws_service import (
    get_loxone_ws_status,
    get_cached_loxone_value,
    get_loxone_ws_cache_sample,
)

from services.loxone_service import (
    get_loxone_structure_summary,
    get_controls_by_room,
    get_controls_by_category,
    get_controls_by_domain,
    get_room_temperature,
    get_room_summary,
    get_audio_controls_by_room,
    get_lighting_controls_by_room,
    get_best_audio_control_candidates,
    get_audio_action_map,
    get_audio_behavior_map,
    find_control_by_name,
    get_audio_tool_targets,
    get_sensor_inventory,
    get_live_values_by_room,
    get_all_live_values,
    get_room_climate_summary,
    get_house_state_summary,
)
from config import INFLUX_ORG, LOXONE_HISTORY_BUCKET, LOXONE_HISTORY_MEASUREMENT
from extensions import query_api






loxone_bp = Blueprint("loxone", __name__)

@loxone_bp.route("/ai/loxone_room_climate", methods=["GET"])
def loxone_room_climate():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_room_climate_summary(room))

@loxone_bp.route("/ai/house_state_summary", methods=["GET"])
def house_state_summary():
    return jsonify(get_house_state_summary())




@loxone_bp.route("/ai/audio_tool_targets", methods=["GET"])
def audio_tool_targets():
    return jsonify(get_audio_tool_targets())


@loxone_bp.route("/ai/audio_resolve_control", methods=["GET"])
def audio_resolve_control():
    room = request.args.get("room", "").strip()
    control_name = request.args.get("control_name", "").strip()

    if not room or not control_name:
        return jsonify({
            "status": "error",
            "message": "Missing required query parameters: room and control_name"
        }), 400

    return jsonify(find_control_by_name(room, control_name))


@loxone_bp.route("/ai/loxone_audio_behavior_map", methods=["GET"])
def loxone_audio_behavior_map():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_audio_behavior_map(room))


@loxone_bp.route("/ai/loxone_audio_action_map", methods=["GET"])
def loxone_audio_action_map():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_audio_action_map(room))


@loxone_bp.route("/ai/loxone_lighting_controls_by_room", methods=["GET"])
def loxone_lighting_controls_by_room():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_lighting_controls_by_room(room))


@loxone_bp.route("/ai/loxone_audio_control_candidates", methods=["GET"])
def loxone_audio_control_candidates():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_best_audio_control_candidates(room))


@loxone_bp.route("/ai/loxone_audio_controls_by_room", methods=["GET"])
def loxone_audio_controls_by_room():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_audio_controls_by_room(room))


@loxone_bp.route("/ai/loxone_room_summary", methods=["GET"])
def loxone_room_summary():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_room_summary(room))


@loxone_bp.route("/ai/loxone_structure_summary", methods=["GET"])
def loxone_structure_summary():
    return jsonify(get_loxone_structure_summary())


@loxone_bp.route("/ai/loxone_controls_by_room", methods=["GET"])
def loxone_controls_by_room():
    room = request.args.get("room", "").strip()
    domain = request.args.get("domain", "").strip() or None
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_controls_by_room(room, domain=domain))


@loxone_bp.route("/ai/loxone_controls_by_category", methods=["GET"])
def loxone_controls_by_category():
    category = request.args.get("category", "").strip()
    if not category:
        return jsonify({"status": "error", "message": "Missing required query parameter: category"}), 400
    return jsonify(get_controls_by_category(category))


@loxone_bp.route("/ai/loxone_controls_by_domain", methods=["GET"])
def loxone_controls_by_domain():
    domain = request.args.get("domain", "").strip()
    if not domain:
        return jsonify({"status": "error", "message": "Missing required query parameter: domain"}), 400
    return jsonify(get_controls_by_domain(domain))


@loxone_bp.route("/ai/loxone_room_temperature", methods=["GET"])
def loxone_room_temperature():
    room = request.args.get("room", "").strip()
    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400
    return jsonify(get_room_temperature(room))


@loxone_bp.route("/ai/loxone_sensor_inventory", methods=["GET"])
def loxone_sensor_inventory():
    room = request.args.get("room", "").strip() or None
    return jsonify(get_sensor_inventory(room_name=room))


@loxone_bp.route("/ai/loxone_live_room", methods=["GET"])
def loxone_live_room():
    room = request.args.get("room", "").strip()
    domain = request.args.get("domain", "").strip() or None
    sensors_only = request.args.get("sensors_only", "1").strip() != "0"

    if not room:
        return jsonify({"status": "error", "message": "Missing required query parameter: room"}), 400

    return jsonify(get_live_values_by_room(room, domain=domain, sensors_only=sensors_only))


@loxone_bp.route("/ai/loxone_live_all", methods=["GET"])
def loxone_live_all():
    domain = request.args.get("domain", "").strip() or None
    sensors_only = request.args.get("sensors_only", "1").strip() != "0"
    return jsonify(get_all_live_values(domain=domain, sensors_only=sensors_only))




@loxone_bp.route("/ai/loxone_ws_status", methods=["GET"])
def loxone_ws_status():
    return jsonify(get_loxone_ws_status())


@loxone_bp.route("/ai/loxone_ws_value", methods=["GET"])
def loxone_ws_value():
    uuid = request.args.get("uuid", "").strip()
    if not uuid:
        return jsonify({
            "status": "error",
            "error": "Missing uuid parameter",
        }), 400

    return jsonify({
        "status": "ok",
        "uuid": uuid,
        "value": get_cached_loxone_value(uuid),
    })


@loxone_bp.route("/ai/loxone_ws_cache_sample", methods=["GET"])
def loxone_ws_cache_sample():
    limit_raw = request.args.get("limit", "50").strip()
    contains = request.args.get("contains", "").strip() or None

    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 50

    return jsonify(get_loxone_ws_cache_sample(limit=limit, contains=contains))



@loxone_bp.route("/ai/loxone_history_recent", methods=["GET"])
def loxone_history_recent():
    room = request.args.get("room", "").strip()
    minutes_raw = request.args.get("minutes", "60").strip()

    try:
        minutes = int(minutes_raw)
    except ValueError:
        minutes = 60

    if minutes < 1:
        minutes = 1
    if minutes > 10080:
        minutes = 10080

    filters = [f'r._measurement == "{LOXONE_HISTORY_MEASUREMENT}"']

    if room:
        safe_room = room.replace('"', '\\"')
        filters.append(f'r.room == "{safe_room}"')

    filter_expr = " and ".join(filters)

    flux = f'''
from(bucket: "{LOXONE_HISTORY_BUCKET}")
  |> range(start: -{minutes}m)
  |> filter(fn: (r) => {filter_expr})
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 200)
'''

    try:
        tables = query_api.query(org=INFLUX_ORG, query=flux)
        items = []

        for table in tables:
            for record in table.records:
                items.append({
                    "time": record.get_time().isoformat() if record.get_time() else None,
                    "measurement": record.get_measurement(),
                    "field": record.get_field(),
                    "value": record.get_value(),
                    "room": record.values.get("room"),
                    "domain": record.values.get("domain"),
                    "sensor_type": record.values.get("sensor_type"),
                    "control_name": record.values.get("control_name"),
                    "control_uuid": record.values.get("control_uuid"),
                    "state_key": record.values.get("state_key"),
                })

        return jsonify({
            "status": "ok",
            "bucket": LOXONE_HISTORY_BUCKET,
            "measurement": LOXONE_HISTORY_MEASUREMENT,
            "room": room or None,
            "minutes": minutes,
            "count": len(items),
            "items": items,
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": str(exc),
            "bucket": LOXONE_HISTORY_BUCKET,
            "measurement": LOXONE_HISTORY_MEASUREMENT,
            "room": room or None,
            "minutes": minutes,
        }), 500


# =========================
# Loxone history AI summary endpoints
# append this whole block at the bottom of routes/loxone_routes.py
# =========================

def _hist_parse_int(raw_value, default_value, min_value=None, max_value=None):
    try:
        value = int(raw_value)
    except Exception:
        value = default_value

    if min_value is not None and value < min_value:
        value = min_value
    if max_value is not None and value > max_value:
        value = max_value
    return value


def _hist_fetch_recent(minutes=30, room=None, limit=2000):
    from services.loxone_history_service import get_recent_loxone_history

    return get_recent_loxone_history(
        minutes=minutes,
        room=room,
        limit=limit,
    )


def _hist_key(item):
    return f"{item.get('control_uuid')}::{item.get('state_key')}"


def _hist_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _hist_truthy(value):
    v = _hist_float(value)
    if v is None:
        return False
    return v > 0


def _hist_sort_desc(items):
    return sorted(items, key=lambda x: str(x.get("time") or ""), reverse=True)


def _hist_latest_per_state(items):
    latest = {}
    for item in _hist_sort_desc(items):
        key = _hist_key(item)
        if key not in latest:
            latest[key] = item
    return latest


def _hist_changes_summary(items):
    grouped = {}

    # sort oldest -> newest so previous/current comparisons make sense
    ordered = sorted(items, key=lambda x: str(x.get("time") or ""))

    for item in ordered:
        key = _hist_key(item)
        bucket = grouped.setdefault(key, {
            "control_uuid": item.get("control_uuid"),
            "control_name": item.get("control_name"),
            "room": item.get("room"),
            "domain": item.get("domain"),
            "sensor_type": item.get("sensor_type"),
            "state_key": item.get("state_key"),
            "current_value": item.get("value"),
            "previous_value": None,
            "first_time": item.get("time"),
            "last_time": item.get("time"),
            "change_count": 0,
            "samples": 0,
        })

        if bucket["samples"] > 0:
            prev_value = bucket["current_value"]
            new_value = item.get("value")
            if prev_value != new_value:
                bucket["previous_value"] = prev_value
                bucket["current_value"] = new_value
                bucket["change_count"] += 1
        else:
            bucket["current_value"] = item.get("value")

        bucket["samples"] += 1
        bucket["last_time"] = item.get("time")

    return list(grouped.values())


def _hist_room_activity_summary(items):
    latest = _hist_latest_per_state(items)

    room_map = {}

    for item in latest.values():
        room = item.get("room") or "unknown"
        domain = item.get("domain") or "unknown"

        bucket = room_map.setdefault(room, {
            "room": room,
            "state_count": 0,
            "active_count": 0,
            "domains": {},
            "active_items": [],
            "last_time": item.get("time"),
        })

        bucket["state_count"] += 1
        bucket["domains"][domain] = bucket["domains"].get(domain, 0) + 1

        item_time = str(item.get("time") or "")
        last_time = str(bucket.get("last_time") or "")
        if item_time > last_time:
            bucket["last_time"] = item.get("time")

        if _hist_truthy(item.get("value")):
            bucket["active_count"] += 1
            bucket["active_items"].append({
                "control_name": item.get("control_name"),
                "state_key": item.get("state_key"),
                "value": item.get("value"),
                "domain": item.get("domain"),
                "sensor_type": item.get("sensor_type"),
                "time": item.get("time"),
            })

    return sorted(room_map.values(), key=lambda x: x["room"])


def _hist_presence_summary(items):
    latest = _hist_latest_per_state(items)
    result = []

    for item in latest.values():
        domain = (item.get("domain") or "").lower()
        sensor_type = (item.get("sensor_type") or "").lower()
        state_key = (item.get("state_key") or "").lower()

        if domain != "presence" and sensor_type not in ("presence", "motion"):
            continue

        if state_key not in ("active", "locked", "events", "time", "activesince"):
            continue

        result.append({
            "room": item.get("room"),
            "control_name": item.get("control_name"),
            "control_uuid": item.get("control_uuid"),
            "sensor_type": item.get("sensor_type"),
            "state_key": item.get("state_key"),
            "value": item.get("value"),
            "is_active": _hist_truthy(item.get("value")),
            "time": item.get("time"),
        })

    return sorted(result, key=lambda x: (str(x.get("room") or ""), str(x.get("control_name") or ""), str(x.get("state_key") or "")))


def _hist_current_active_summary(items):
    latest = _hist_latest_per_state(items)
    active_items = []

    for item in latest.values():
        if _hist_truthy(item.get("value")):
            active_items.append({
                "room": item.get("room"),
                "domain": item.get("domain"),
                "sensor_type": item.get("sensor_type"),
                "control_name": item.get("control_name"),
                "control_uuid": item.get("control_uuid"),
                "state_key": item.get("state_key"),
                "value": item.get("value"),
                "time": item.get("time"),
            })

    active_items = sorted(
        active_items,
        key=lambda x: (
            str(x.get("room") or ""),
            str(x.get("domain") or ""),
            str(x.get("control_name") or ""),
            str(x.get("state_key") or ""),
        )
    )

    return active_items


def _hist_last_change_summary(items):
    latest = _hist_latest_per_state(items)

    by_room = {}
    by_control = {}

    for item in latest.values():
        room = item.get("room") or "unknown"
        control_uuid = item.get("control_uuid") or "unknown"

        existing_room = by_room.get(room)
        if existing_room is None or str(item.get("time") or "") > str(existing_room.get("time") or ""):
            by_room[room] = {
                "room": room,
                "control_name": item.get("control_name"),
                "control_uuid": item.get("control_uuid"),
                "state_key": item.get("state_key"),
                "value": item.get("value"),
                "time": item.get("time"),
                "domain": item.get("domain"),
                "sensor_type": item.get("sensor_type"),
            }

        existing_control = by_control.get(control_uuid)
        if existing_control is None or str(item.get("time") or "") > str(existing_control.get("time") or ""):
            by_control[control_uuid] = {
                "room": item.get("room"),
                "control_name": item.get("control_name"),
                "control_uuid": item.get("control_uuid"),
                "state_key": item.get("state_key"),
                "value": item.get("value"),
                "time": item.get("time"),
                "domain": item.get("domain"),
                "sensor_type": item.get("sensor_type"),
            }

    return {
        "rooms": sorted(by_room.values(), key=lambda x: x["room"]),
        "controls": sorted(by_control.values(), key=lambda x: (str(x.get("room") or ""), str(x.get("control_name") or ""))),
    }


@loxone_bp.route("/ai/loxone_history_recent_summary", methods=["GET"])
def loxone_history_recent_summary():
    minutes = _hist_parse_int(request.args.get("minutes", "30"), 30, 1, 1440)
    limit = _hist_parse_int(request.args.get("limit", "2000"), 2000, 1, 10000)
    room = request.args.get("room", "").strip() or None

    data = _hist_fetch_recent(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    summary_items = _hist_changes_summary(data.get("items", []))
    summary_items = sorted(
        summary_items,
        key=lambda x: (
            str(x.get("room") or ""),
            str(x.get("control_name") or ""),
            str(x.get("state_key") or ""),
        )
    )

    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "source_count": data.get("count", 0),
        "summary_count": len(summary_items),
        "items": summary_items,
    })


@loxone_bp.route("/ai/loxone_history_room_activity", methods=["GET"])
def loxone_history_room_activity():
    minutes = _hist_parse_int(request.args.get("minutes", "30"), 30, 1, 1440)
    limit = _hist_parse_int(request.args.get("limit", "3000"), 3000, 1, 10000)
    room = request.args.get("room", "").strip() or None

    data = _hist_fetch_recent(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _hist_room_activity_summary(data.get("items", []))

    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "room_count": len(items),
        "items": items,
    })


@loxone_bp.route("/ai/loxone_history_presence_summary", methods=["GET"])
def loxone_history_presence_summary():
    minutes = _hist_parse_int(request.args.get("minutes", "30"), 30, 1, 1440)
    limit = _hist_parse_int(request.args.get("limit", "3000"), 3000, 1, 10000)
    room = request.args.get("room", "").strip() or None

    data = _hist_fetch_recent(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _hist_presence_summary(data.get("items", []))

    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    })


@loxone_bp.route("/ai/loxone_history_current_active", methods=["GET"])
def loxone_history_current_active():
    minutes = _hist_parse_int(request.args.get("minutes", "30"), 30, 1, 1440)
    limit = _hist_parse_int(request.args.get("limit", "3000"), 3000, 1, 10000)
    room = request.args.get("room", "").strip() or None

    data = _hist_fetch_recent(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _hist_current_active_summary(data.get("items", []))

    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    })


@loxone_bp.route("/ai/loxone_history_last_change", methods=["GET"])
def loxone_history_last_change():
    minutes = _hist_parse_int(request.args.get("minutes", "60"), 60, 1, 10080)
    limit = _hist_parse_int(request.args.get("limit", "5000"), 5000, 1, 20000)
    room = request.args.get("room", "").strip() or None

    data = _hist_fetch_recent(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    summary = _hist_last_change_summary(data.get("items", []))

    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "rooms_count": len(summary["rooms"]),
        "controls_count": len(summary["controls"]),
        "rooms": summary["rooms"],
        "controls": summary["controls"],
    })




# =========================
# Smart AI-friendly Loxone history endpoints
# append this whole block at the bottom of routes/loxone_routes.py
# =========================

def _ai_parse_int(raw_value, default_value, min_value=None, max_value=None):
    try:
        value = int(raw_value)
    except Exception:
        value = default_value

    if min_value is not None and value < min_value:
        value = min_value
    if max_value is not None and value > max_value:
        value = max_value
    return value


def _ai_fetch_history(minutes=30, room=None, limit=4000):
    from services.loxone_history_service import get_recent_loxone_history
    return get_recent_loxone_history(minutes=minutes, room=room, limit=limit)


def _ai_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _ai_key(item):
    return f"{item.get('control_uuid')}::{item.get('state_key')}"


def _ai_sorted_desc(items):
    return sorted(items, key=lambda x: str(x.get("time") or ""), reverse=True)


def _ai_latest_per_state(items):
    latest = {}
    for item in _ai_sorted_desc(items):
        key = _ai_key(item)
        if key not in latest:
            latest[key] = item
    return latest


def _ai_is_binaryish_state(item):
    state_key = str(item.get("state_key") or "").lower()
    domain = str(item.get("domain") or "").lower()
    sensor_type = str(item.get("sensor_type") or "").lower()
    value = _ai_float(item.get("value"))

    allowed_keys = {
        "active", "locked", "lockedon", "ison", "isoff", "bell",
        "arealarmsignalsoff", "resetactive", "mute", "disabled",
        "openwindow", "isenabled", "isalarmactive", "currentstatus"
    }

    allowed_domains = {
        "presence", "security", "lighting", "audio", "access", "switch"
    }

    allowed_sensor_types = {
        "presence", "motion", "security", "lighting",
        "audio_control", "door_window", "switch", "access_control"
    }

    if state_key in allowed_keys:
        return True
    if domain in allowed_domains and value in (0.0, 1.0):
        return True
    if sensor_type in allowed_sensor_types and value in (0.0, 1.0):
        return True
    return False


def _ai_is_presence_like(item):
    domain = str(item.get("domain") or "").lower()
    sensor_type = str(item.get("sensor_type") or "").lower()
    state_key = str(item.get("state_key") or "").lower()

    if domain == "presence":
        return True
    if sensor_type in {"presence", "motion"}:
        return True
    if state_key in {"active", "activesince", "events"} and sensor_type in {"presence", "motion"}:
        return True
    return False


def _ai_is_telemetry(item):
    return not _ai_is_binaryish_state(item)


def _ai_is_on(item):
    value = _ai_float(item.get("value"))
    if value is None:
        return False
    return value > 0


def _ai_compact_item(item):
    return {
        "room": item.get("room"),
        "domain": item.get("domain"),
        "sensor_type": item.get("sensor_type"),
        "control_name": item.get("control_name"),
        "control_uuid": item.get("control_uuid"),
        "state_key": item.get("state_key"),
        "value": item.get("value"),
        "time": item.get("time"),
    }


def _ai_group_room_states(items):
    latest = _ai_latest_per_state(items)
    rooms = {}

    for item in latest.values():
        room = item.get("room") or "unknown"
        bucket = rooms.setdefault(room, {
            "room": room,
            "binary_state_count": 0,
            "binary_on_count": 0,
            "telemetry_count": 0,
            "on_items": [],
            "latest_time": item.get("time"),
        })

        item_time = str(item.get("time") or "")
        latest_time = str(bucket.get("latest_time") or "")
        if item_time > latest_time:
            bucket["latest_time"] = item.get("time")

        if _ai_is_binaryish_state(item):
            bucket["binary_state_count"] += 1
            if _ai_is_on(item):
                bucket["binary_on_count"] += 1
                bucket["on_items"].append(_ai_compact_item(item))
        else:
            bucket["telemetry_count"] += 1

    return sorted(rooms.values(), key=lambda x: x["room"])


def _ai_binary_on_items(items):
    latest = _ai_latest_per_state(items)
    result = []

    for item in latest.values():
        if not _ai_is_binaryish_state(item):
            continue
        if not _ai_is_on(item):
            continue
        result.append(_ai_compact_item(item))

    return sorted(result, key=lambda x: (
        str(x.get("room") or ""),
        str(x.get("domain") or ""),
        str(x.get("control_name") or ""),
        str(x.get("state_key") or ""),
    ))


def _ai_presence_items(items):
    latest = _ai_latest_per_state(items)
    result = []

    for item in latest.values():
        if not _ai_is_presence_like(item):
            continue
        result.append({
            "room": item.get("room"),
            "control_name": item.get("control_name"),
            "control_uuid": item.get("control_uuid"),
            "sensor_type": item.get("sensor_type"),
            "state_key": item.get("state_key"),
            "value": item.get("value"),
            "is_active": _ai_is_on(item),
            "time": item.get("time"),
        })

    return sorted(result, key=lambda x: (
        str(x.get("room") or ""),
        str(x.get("control_name") or ""),
        str(x.get("state_key") or ""),
    ))


def _ai_telemetry_latest(items):
    latest = _ai_latest_per_state(items)
    result = []

    for item in latest.values():
        if not _ai_is_telemetry(item):
            continue
        result.append(_ai_compact_item(item))

    return sorted(result, key=lambda x: (
        str(x.get("room") or ""),
        str(x.get("domain") or ""),
        str(x.get("control_name") or ""),
        str(x.get("state_key") or ""),
    ))


def _ai_binary_changes(items):
    ordered = sorted(items, key=lambda x: str(x.get("time") or ""))
    grouped = {}

    for item in ordered:
        if not _ai_is_binaryish_state(item):
            continue

        key = _ai_key(item)
        bucket = grouped.setdefault(key, {
            "room": item.get("room"),
            "domain": item.get("domain"),
            "sensor_type": item.get("sensor_type"),
            "control_name": item.get("control_name"),
            "control_uuid": item.get("control_uuid"),
            "state_key": item.get("state_key"),
            "first_time": item.get("time"),
            "last_time": item.get("time"),
            "previous_value": None,
            "current_value": item.get("value"),
            "change_count": 0,
            "samples": 0,
        })

        current_value = item.get("value")
        if bucket["samples"] > 0 and bucket["current_value"] != current_value:
            bucket["previous_value"] = bucket["current_value"]
            bucket["current_value"] = current_value
            bucket["change_count"] += 1
        else:
            bucket["current_value"] = current_value

        bucket["samples"] += 1
        bucket["last_time"] = item.get("time")

    result = list(grouped.values())
    result = sorted(result, key=lambda x: (
        str(x.get("room") or ""),
        str(x.get("control_name") or ""),
        str(x.get("state_key") or ""),
    ))
    return result


@loxone_bp.route("/ai/loxone_history_binary_active", methods=["GET"])
def loxone_history_binary_active():
    minutes = _ai_parse_int(request.args.get("minutes", "60"), 60, 1, 1440)
    limit = _ai_parse_int(request.args.get("limit", "5000"), 5000, 1, 20000)
    room = request.args.get("room", "").strip() or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _ai_binary_on_items(data.get("items", []))
    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    })


@loxone_bp.route("/ai/loxone_history_binary_changes", methods=["GET"])
def loxone_history_binary_changes():
    minutes = _ai_parse_int(request.args.get("minutes", "60"), 60, 1, 10080)
    limit = _ai_parse_int(request.args.get("limit", "8000"), 8000, 1, 50000)
    room = request.args.get("room", "").strip() or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _ai_binary_changes(data.get("items", []))
    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    })


@loxone_bp.route("/ai/loxone_history_presence_ai", methods=["GET"])
def loxone_history_presence_ai():
    minutes = _ai_parse_int(request.args.get("minutes", "60"), 60, 1, 1440)
    limit = _ai_parse_int(request.args.get("limit", "5000"), 5000, 1, 20000)
    room = request.args.get("room", "").strip() or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _ai_presence_items(data.get("items", []))
    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(items),
        "items": items,
    })


@loxone_bp.route("/ai/loxone_history_telemetry_latest", methods=["GET"])
def loxone_history_telemetry_latest():
    minutes = _ai_parse_int(request.args.get("minutes", "120"), 120, 1, 10080)
    limit = _ai_parse_int(request.args.get("limit", "8000"), 8000, 1, 50000)
    room = request.args.get("room", "").strip() or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _ai_telemetry_latest(data.get("items", []))

    filtered_items = []
    for item in items:
        item_room = item.get("room")
        state_key = item.get("state_key")
        value = item.get("value")

        if item_room == "Not Assigned":
            continue

        if state_key not in {"tempActual", "humidityActual"}:
            continue

        if value in (None, -1000.0, -999.0):
            continue

        if state_key == "humidityActual":
            try:
                if float(value) == 0.0:
                    continue
            except (TypeError, ValueError):
                continue

        filtered_items.append(item)

    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "count": len(filtered_items),
        "items": filtered_items,
    })


@loxone_bp.route("/ai/loxone_history_room_activity_ai", methods=["GET"])
def loxone_history_room_activity_ai():
    minutes = _ai_parse_int(request.args.get("minutes", "60"), 60, 1, 1440)
    limit = _ai_parse_int(request.args.get("limit", "8000"), 8000, 1, 50000)
    room = request.args.get("room", "").strip() or None

    data = _ai_fetch_history(minutes=minutes, room=room, limit=limit)
    if data.get("status") != "ok":
        return jsonify(data), 500

    items = _ai_group_room_states(data.get("items", []))
    return jsonify({
        "status": "ok",
        "minutes": minutes,
        "room": room,
        "room_count": len(items),
        "items": items,
    })
