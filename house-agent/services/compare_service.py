import re
from datetime import datetime, timezone

from services.influx_helpers import iso_z, read_flux_values_for_field


def period_stats_for_field(field: str, start_iso: str, stop_iso: str) -> dict:
    values = read_flux_values_for_field(field, start_iso, stop_iso)

    if not values:
        return {
            "field": field,
            "range_start": start_iso,
            "range_stop": stop_iso,
            "samples": 0,
            "min": None,
            "max": None,
            "avg": None,
            "latest": None,
        }

    return {
        "field": field,
        "range_start": start_iso,
        "range_stop": stop_iso,
        "samples": len(values),
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "latest": values[-1],
    }


def compare_period_stats(a: dict, b: dict) -> dict:
    avg_a = a["avg"]
    avg_b = b["avg"]

    avg_delta = None
    status = "unknown"

    if avg_a is not None and avg_b is not None:
        avg_delta = avg_a - avg_b

        if abs(avg_delta) <= max(25, abs(avg_b) * 0.05):
            status = "similar"
        elif avg_delta > 0:
            status = "higher"
        else:
            status = "lower"

    return {
        "field": a["field"],
        "period_1": a,
        "period_2": b,
        "avg_delta": avg_delta,
        "status": status,
    }


def parse_compare_periods_question(question: str):
    q = question.strip().lower()

    metric_map = {
        "power": "total_power",
        "total_power": "total_power",
        "frequency": "frequency",
        "pf": "total_pf",
        "power factor": "total_pf",
        "reactive": "total_var",
        "reactive power": "total_var",
        "apparent": "total_va",
        "apparent power": "total_va",
    }

    pattern = re.compile(
        r"compare\s+(?P<metric>[a-zA-Z_ ]+)\s+from\s+"
        r"(?P<s1>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+to\s+"
        r"(?P<e1>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+vs\s+"
        r"(?P<s2>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+to\s+"
        r"(?P<e2>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})"
    )

    match = pattern.search(q)
    if not match:
        return None

    metric_raw = match.group("metric").strip()
    field = metric_map.get(metric_raw)
    if not field:
        return None

    def parse_local(ts: str) -> str:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        return iso_z(dt)

    return {
        "field": field,
        "start_1": parse_local(match.group("s1")),
        "stop_1": parse_local(match.group("e1")),
        "start_2": parse_local(match.group("s2")),
        "stop_2": parse_local(match.group("e2")),
    }
