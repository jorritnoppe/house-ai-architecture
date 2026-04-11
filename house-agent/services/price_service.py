from datetime import datetime, timedelta, timezone

from config import (
    INFLUX_BUCKET,
    INFLUX_MEASUREMENT,
    PRICE_INFLUX_BUCKET,
    PRICE_INFLUX_MEASUREMENT,
    PRICE_INFLUX_FIELD,
    PRICE_WINDOW,
)
from extensions import query_api
from services.influx_helpers import iso_z


def query_latest_price(range_window: str = "-7d"):
    flux = f"""
from(bucket: "{PRICE_INFLUX_BUCKET}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{PRICE_INFLUX_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "{PRICE_INFLUX_FIELD}")
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


def read_price_series(start_iso: str, stop_iso: str, window: str | None = None):
    window = window or PRICE_WINDOW

    flux = f"""
from(bucket: "{PRICE_INFLUX_BUCKET}")
  |> range(start: time(v: "{start_iso}"), stop: time(v: "{stop_iso}"))
  |> filter(fn: (r) => r._measurement == "{PRICE_INFLUX_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "{PRICE_INFLUX_FIELD}")
  |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])
"""
    tables = query_api.query(flux)

    rows = []
    for table in tables:
        for record in table.records:
            rows.append({
                "time": record.get_time().isoformat(),
                "price_eur_per_kwh": float(record.get_value()),
            })
    return rows


def read_import_counter_series(start_iso: str, stop_iso: str, window: str | None = None):
    window = window or PRICE_WINDOW

    flux = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: time(v: "{start_iso}"), stop: time(v: "{stop_iso}"))
  |> filter(fn: (r) => r._measurement == "{INFLUX_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "import_kWh")
  |> aggregateWindow(every: {window}, fn: last, createEmpty: false)
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])
"""
    tables = query_api.query(flux)

    rows = []
    for table in tables:
        for record in table.records:
            rows.append({
                "time": record.get_time().isoformat(),
                "import_kwh_counter": float(record.get_value()),
            })
    return rows


def calculate_cost_from_counters(start_iso: str, stop_iso: str, window: str | None = None):
    window = window or PRICE_WINDOW

    prices = read_price_series(start_iso, stop_iso, window=window)
    imports = read_import_counter_series(start_iso, stop_iso, window=window)

    if len(prices) < 1 or len(imports) < 2:
        return {
            "status": "no_data",
            "range_start": start_iso,
            "range_stop": stop_iso,
            "window": window,
            "matched_points": 0,
            "total_import_kwh": None,
            "total_cost_eur": None,
            "average_price_eur_per_kwh": None,
            "breakdown": [],
        }

    price_map = {row["time"]: row["price_eur_per_kwh"] for row in prices}

    breakdown = []
    total_cost = 0.0
    total_import_kwh = 0.0

    previous = None
    for row in imports:
        if previous is None:
            previous = row
            continue

        ts = row["time"]
        if ts not in price_map:
            previous = row
            continue

        delta_kwh = row["import_kwh_counter"] - previous["import_kwh_counter"]
        if delta_kwh < 0:
            delta_kwh = 0.0

        price = price_map[ts]
        cost = delta_kwh * price

        total_import_kwh += delta_kwh
        total_cost += cost

        breakdown.append({
            "time": ts,
            "price_eur_per_kwh": round(price, 6),
            "import_kwh": round(delta_kwh, 6),
            "cost_eur": round(cost, 6),
        })

        previous = row

    avg_price = (total_cost / total_import_kwh) if total_import_kwh > 0 else None

    return {
        "status": "ok" if breakdown else "no_data",
        "range_start": start_iso,
        "range_stop": stop_iso,
        "window": window,
        "matched_points": len(breakdown),
        "total_import_kwh": round(total_import_kwh, 4) if total_import_kwh is not None else None,
        "total_cost_eur": round(total_cost, 4) if total_cost is not None else None,
        "average_price_eur_per_kwh": round(avg_price, 6) if avg_price is not None else None,
        "price_source": {
            "bucket": PRICE_INFLUX_BUCKET,
            "measurement": PRICE_INFLUX_MEASUREMENT,
            "field": PRICE_INFLUX_FIELD,
        },
        "import_source": {
            "bucket": INFLUX_BUCKET,
            "measurement": INFLUX_MEASUREMENT,
            "field": "import_kWh",
        },
        "breakdown": breakdown,
    }


def get_electricity_cost_today():
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return calculate_cost_from_counters(iso_z(today_start), iso_z(now), window=PRICE_WINDOW)


def get_electricity_cost_last_24h():
    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(hours=24)
    return calculate_cost_from_counters(iso_z(start_dt), iso_z(now), window=PRICE_WINDOW)


def get_cheapest_hours_today(limit: int = 3):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    prices = read_price_series(iso_z(today_start), iso_z(now), window=PRICE_WINDOW)
    ranked = sorted(prices, key=lambda x: x["price_eur_per_kwh"])[:limit]

    return {
        "status": "ok" if ranked else "no_data",
        "count": len(ranked),
        "items": ranked,
    }
