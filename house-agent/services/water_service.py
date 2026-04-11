from datetime import datetime

from config import (
    SALT_INFLUX_BUCKET,
    SALT_INFLUX_MEASUREMENT,
    SALT_INFLUX_FIELD,
    SALT_FULL_CM,
    SALT_EMPTY_CM,
    WATER_TEMP_BUCKET,
    WATER_TEMP_MEASUREMENT,
    WATER_TEMP1_FIELD,
    WATER_TEMP2_FIELD,
    WATER_TEMP1_DIVISOR,
)
from extensions import query_api


WATER_FLOW_FIELD = "flow_lpm"


def query_latest_salt_distance(range_window: str = "-30d"):
    flux = f"""
from(bucket: "{SALT_INFLUX_BUCKET}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{SALT_INFLUX_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "{SALT_INFLUX_FIELD}")
  |> last()
"""
    tables = query_api.query(flux)

    for table in tables:
        for record in table.records:
            value = record.get_value()
            time_ = record.get_time()
            return {
                "measurement": record.get_measurement(),
                "field": record.get_field(),
                "value": float(value) if value is not None else None,
                "time": time_.isoformat() if isinstance(time_, datetime) else str(time_),
            }

    return None


def salt_level_percent_from_distance(distance_cm: float) -> float:
    if SALT_EMPTY_CM <= SALT_FULL_CM:
        raise ValueError("SALT_EMPTY_CM must be greater than SALT_FULL_CM")

    pct = ((SALT_EMPTY_CM - distance_cm) / (SALT_EMPTY_CM - SALT_FULL_CM)) * 100.0
    return max(0.0, min(100.0, pct))


def salt_level_status_from_percent(percent: float) -> str:
    if percent >= 80:
        return "good"
    if percent >= 50:
        return "okay"
    if percent >= 25:
        return "low"
    return "critical"


def get_salt_tank_level():
    latest = query_latest_salt_distance(range_window="-30d")

    if not latest or latest["value"] is None:
        return {
            "status": "no_data",
            "message": "No salt tank level data found in InfluxDB.",
        }

    distance_cm = float(latest["value"])
    percent = salt_level_percent_from_distance(distance_cm)

    return {
        "status": "ok",
        "distance_cm": round(distance_cm, 2),
        "salt_level_percent": round(percent, 1),
        "salt_level_status": salt_level_status_from_percent(percent),
        "timestamp": latest["time"],
        "source": {
            "bucket": SALT_INFLUX_BUCKET,
            "measurement": SALT_INFLUX_MEASUREMENT,
            "field": SALT_INFLUX_FIELD,
        },
    }


def query_latest_water_temps(range_window: str = "-30d"):
    flux = f"""
from(bucket: "{WATER_TEMP_BUCKET}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{WATER_TEMP_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "{WATER_TEMP1_FIELD}" or r._field == "{WATER_TEMP2_FIELD}")
  |> last()
"""
    tables = query_api.query(flux)

    result = {
        WATER_TEMP1_FIELD: None,
        WATER_TEMP2_FIELD: None,
    }

    for table in tables:
        for record in table.records:
            field = record.get_field()
            value = record.get_value()
            time_ = record.get_time()

            result[field] = {
                "value": float(value) if value is not None else None,
                "time": time_.isoformat() if isinstance(time_, datetime) else str(time_),
            }

    return result


def water_temp_status(temp_c: float | None) -> str:
    if temp_c is None:
        return "unknown"
    if temp_c < 5:
        return "very_cold"
    if temp_c < 12:
        return "cold"
    if temp_c < 22:
        return "cool"
    if temp_c < 30:
        return "warm"
    return "hot"


def get_water_temperature_summary():
    data = query_latest_water_temps(range_window="-30d")

    temp1 = data.get(WATER_TEMP1_FIELD)
    temp2 = data.get(WATER_TEMP2_FIELD)

    temp1_raw = temp1["value"] if temp1 and temp1["value"] is not None else None
    temp2_raw = temp2["value"] if temp2 and temp2["value"] is not None else None

    inlet_temp_c = temp1_raw / WATER_TEMP1_DIVISOR if temp1_raw is not None else None
    salt_tank_temp_c = temp2_raw

    timestamps = [x["time"] for x in [temp1, temp2] if x and x.get("time")]
    latest_time = max(timestamps) if timestamps else None

    if inlet_temp_c is None and salt_tank_temp_c is None:
        return {
            "status": "no_data",
            "message": "No water temperature data found in InfluxDB.",
        }

    temp_delta = None
    if inlet_temp_c is not None and salt_tank_temp_c is not None:
        temp_delta = salt_tank_temp_c - inlet_temp_c

    return {
        "status": "ok",
        "timestamp": latest_time,
        "inlet_water_temp_c": round(inlet_temp_c, 2) if inlet_temp_c is not None else None,
        "inlet_water_temp_status": water_temp_status(inlet_temp_c),
        "salt_tank_water_temp_c": round(salt_tank_temp_c, 2) if salt_tank_temp_c is not None else None,
        "salt_tank_water_temp_status": water_temp_status(salt_tank_temp_c),
        "temp_delta_c": round(temp_delta, 2) if temp_delta is not None else None,
        "raw": {
            "temp1_c_raw": temp1_raw,
            "temp2_c_raw": temp2_raw,
            "temp1_divisor": WATER_TEMP1_DIVISOR,
        },
        "source": {
            "bucket": WATER_TEMP_BUCKET,
            "measurement": WATER_TEMP_MEASUREMENT,
            "fields": [WATER_TEMP1_FIELD, WATER_TEMP2_FIELD],
        },
    }


def query_latest_water_flow(range_window: str = "-7d"):
    flux = f"""
from(bucket: "{WATER_TEMP_BUCKET}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{WATER_TEMP_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "{WATER_FLOW_FIELD}")
  |> last()
"""
    tables = query_api.query(flux)

    for table in tables:
        for record in table.records:
            value = record.get_value()
            time_ = record.get_time()
            return {
                "measurement": record.get_measurement(),
                "field": record.get_field(),
                "value": float(value) if value is not None else None,
                "time": time_.isoformat() if isinstance(time_, datetime) else str(time_),
            }

    return None


def get_water_flow_summary():
    latest = query_latest_water_flow(range_window="-7d")

    if not latest or latest["value"] is None:
        return {
            "status": "no_data",
            "message": "No water flow data found in InfluxDB.",
        }

    flow_lpm = float(latest["value"])
    active = flow_lpm > 0.05

    return {
        "status": "ok",
        "timestamp": latest["time"],
        "flow_lpm": round(flow_lpm, 3),
        "flow_active": active,
        "flow_status": "running" if active else "idle",
        "source": {
            "bucket": WATER_TEMP_BUCKET,
            "measurement": WATER_TEMP_MEASUREMENT,
            "field": WATER_FLOW_FIELD,
        },
    }


def get_water_softener_overview():
    salt = get_salt_tank_level()
    temps = get_water_temperature_summary()
    flow = get_water_flow_summary()

    if (
        salt.get("status") != "ok"
        and temps.get("status") != "ok"
        and flow.get("status") != "ok"
    ):
        return {
            "status": "error",
            "message": "No water softener data found",
        }

    refill_warning = None
    if salt.get("status") == "ok":
        pct = salt.get("salt_level_percent")
        if pct is not None:
            if pct <= 10:
                refill_warning = "urgent_refill"
            elif pct <= 25:
                refill_warning = "refill_recommended"
            else:
                refill_warning = "ok"

    return {
        "status": "ok",
        "salt": salt,
        "temperatures": temps,
        "flow": flow,
        "refill_warning": refill_warning,
    }
