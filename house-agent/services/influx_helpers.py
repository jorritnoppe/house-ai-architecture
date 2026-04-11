from datetime import datetime, timezone

from config import INFLUX_BUCKET, INFLUX_MEASUREMENT
from extensions import query_api


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_field_filter(fields: list[str]) -> str:
    return " or ".join([f'r._field == "{field}"' for field in fields])


def query_latest_for_fields(fields: list[str], range_window: str = "-30d") -> dict:
    if not fields:
        return {}

    field_filter = build_field_filter(fields)

    flux = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{INFLUX_MEASUREMENT}")
  |> filter(fn: (r) => {field_filter})
  |> last()
"""

    tables = query_api.query(flux)
    result = {field: None for field in fields}

    for table in tables:
        for record in table.records:
            field = record.get_field()
            value = record.get_value()
            time_ = record.get_time()

            tags = {
                k: v
                for k, v in record.values.items()
                if k not in {"_time", "_value", "_field", "_measurement", "result", "table"}
            }

            result[field] = {
                "measurement": record.get_measurement(),
                "field": field,
                "value": float(value) if value is not None else None,
                "time": time_.isoformat() if isinstance(time_, datetime) else str(time_),
                "tags": tags,
            }

    return result


def read_flux_values_for_field(field: str, start_iso: str, stop_iso: str) -> list[float]:
    flux = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: time(v: "{start_iso}"), stop: time(v: "{stop_iso}"))
  |> filter(fn: (r) => r._measurement == "{INFLUX_MEASUREMENT}")
  |> filter(fn: (r) => r._field == "{field}")
"""
    tables = query_api.query(flux)
    values = []

    for table in tables:
        for record in table.records:
            values.append(float(record.get_value()))

    return values
