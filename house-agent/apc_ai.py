# apc_ai.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


APC_BUCKET_DEFAULT = "apcdata"
APC_MEASUREMENTS_DEFAULT = ["apc_ups", "apc_ups2"]


@dataclass
class APCDeviceSnapshot:
    measurement: str
    fields: Dict[str, Any]
    timestamp: Optional[str] = None


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_status(status: str) -> str:
    return _safe_str(status).upper()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _years_since(date_str: Optional[str]) -> Optional[float]:
    if not date_str:
        return None

    # APC/NUT battery date often looks like 2023-11-19 or 11/19/23
    candidates = [
        "%Y-%m-%d",
        "%m/%d/%y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]

    parsed = None
    for fmt in candidates:
        try:
            parsed = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            break
        except Exception:
            continue

    if not parsed:
        return None

    now = datetime.now(timezone.utc)
    return (now - parsed).days / 365.25


def query_latest_apc_snapshot(
    query_api,
    org: str,
    bucket: str = APC_BUCKET_DEFAULT,
    measurements: Optional[List[str]] = None,
) -> List[APCDeviceSnapshot]:
    """
    Reads the latest available value for each APC field from InfluxDB.
    Assumes data is written in standard line protocol with _measurement / _field / _value.
    """
    measurements = measurements or APC_MEASUREMENTS_DEFAULT
    snapshots: List[APCDeviceSnapshot] = []

    for measurement in measurements:
        flux = f'''
from(bucket: "{bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> last()
'''
        try:
            tables = query_api.query(org=org, query=flux)
        except Exception:
            continue

        fields: Dict[str, Any] = {}
        latest_ts: Optional[str] = None

        for table in tables:
            for record in table.records:
                field_name = record.get_field()
                field_value = record.get_value()
                fields[field_name] = field_value

                ts = record.get_time()
                if ts is not None:
                    ts_str = ts.isoformat()
                    if latest_ts is None or ts_str > latest_ts:
                        latest_ts = ts_str

        if fields:
            snapshots.append(APCDeviceSnapshot(
                measurement=measurement,
                fields=fields,
                timestamp=latest_ts
            ))

    return snapshots


def _device_label(snapshot: APCDeviceSnapshot) -> str:
    name = _safe_str(snapshot.fields.get("upsname"))
    model = _safe_str(snapshot.fields.get("model"))
    serial = _safe_str(snapshot.fields.get("serialno"))

    if name:
        return name
    if model and serial:
        return f"{model} ({serial})"
    if model:
        return model
    return snapshot.measurement


def _derive_apc_conclusions(snapshot: APCDeviceSnapshot) -> Dict[str, Any]:
    f = snapshot.fields

    status = _normalize_status(f.get("status"))
    loadpct = _to_float(f.get("loadpct"))
    bcharge = _to_float(f.get("bcharge"))
    timeleft = _to_float(f.get("timeleft"))
    linev = _to_float(f.get("linev"))
    battv = _to_float(f.get("battv"))
    lotrans = _to_float(f.get("lotrans"))
    hitrans = _to_float(f.get("hitrans"))
    maxlinev = _to_float(f.get("maxlinev") or f.get("maxline"))
    minlinev = _to_float(f.get("minlinev") or f.get("minline"))
    tonbatt = _to_float(f.get("tonbatt"))
    cumonbatt = _to_float(f.get("cumonbatt"))
    numxfers = _to_int(f.get("numxfers"))
    battdate = _safe_str(f.get("battdate"))
    upsname = _device_label(snapshot)

    on_battery = ("OB" in status) or ("ONBATT" in status)
    replace_battery = ("RB" in status) or ("REPLACE" in status)
    overloaded = ("OVER" in status) or (loadpct is not None and loadpct >= 85)

    # Only treat as low battery when it is explicitly low,
    # or when battery charge is genuinely low,
    # or when it is already running on battery and runtime is critically short.
    low_battery = (
        ("LB" in status)
        or (bcharge is not None and bcharge < 25)
        or (on_battery and timeleft is not None and timeleft < 5)
    )



    # Runtime concern is separate from low battery.
    runtime_limited = timeleft is not None and timeleft < 10

    line_out_of_range = False
    if linev is not None and lotrans is not None and hitrans is not None:
        line_out_of_range = (linev < lotrans) or (linev > hitrans)

    battery_age_years = _years_since(battdate)
    aging_battery = battery_age_years is not None and battery_age_years >= 4.0

    severity = "ok"
    if runtime_limited or aging_battery or overloaded or line_out_of_range or on_battery:
        severity = "warning"
    if low_battery or replace_battery:
        severity = "critical"





    conclusions: List[str] = []



    if on_battery:
        conclusions.append("UPS is currently running on battery power")
    else:
        conclusions.append("UPS is running on mains power")

    if loadpct is not None:
        if loadpct >= 85:
            conclusions.append(f"load is high at {loadpct:.1f}%")
        elif loadpct >= 60:
            conclusions.append(f"load is moderate at {loadpct:.1f}%")
        else:
            conclusions.append(f"load is comfortable at {loadpct:.1f}%")

    if timeleft is not None:
        if on_battery:
            if timeleft < 5:
                conclusions.append(f"runtime is critically short at {timeleft:.1f} minutes while on battery")
            elif timeleft < 15:
                conclusions.append(f"runtime is limited at {timeleft:.1f} minutes while on battery")
            else:
                conclusions.append(f"runtime while on battery is {timeleft:.1f} minutes")
        else:
            if timeleft < 10:
                conclusions.append(f"estimated backup runtime is only {timeleft:.1f} minutes at the current load")
            elif timeleft < 30:
                conclusions.append(f"estimated backup runtime is moderate at {timeleft:.1f} minutes")
            else:
                conclusions.append(f"estimated backup runtime looks healthy at {timeleft:.1f} minutes")



    if bcharge is not None:
        if bcharge < 25:
            conclusions.append(f"battery charge is low at {bcharge:.1f}%")
        elif bcharge < 80:
            conclusions.append(f"battery is partially charged at {bcharge:.1f}%")
        else:
            conclusions.append(f"battery charge is good at {bcharge:.1f}%")

    if linev is not None:
        if line_out_of_range:
            conclusions.append(f"input voltage {linev:.1f}V is outside the transfer window")
        else:
            conclusions.append(f"input voltage {linev:.1f}V is within the configured transfer window")

    if numxfers is not None and numxfers > 0:
        conclusions.append(f"recorded transfer events: {numxfers}")

    if cumonbatt is not None and cumonbatt > 0:
        conclusions.append(f"cumulative time on battery: {cumonbatt:.1f} seconds")

    if tonbatt is not None and tonbatt > 0:
        conclusions.append(f"current battery session duration: {tonbatt:.1f} seconds")

    if aging_battery:
        conclusions.append(f"battery age is about {battery_age_years:.1f} years and should be reviewed")
    elif battery_age_years is not None:
        conclusions.append(f"battery age is about {battery_age_years:.1f} years")

    return {
        "device": upsname,
        "measurement": snapshot.measurement,
        "timestamp": snapshot.timestamp,
        "status": status,
        "severity": severity,
        "on_battery": on_battery,
        "low_battery": low_battery,
        "overloaded": overloaded,
        "replace_battery": replace_battery,
        "line_out_of_range": line_out_of_range,
        "loadpct": loadpct,
        "bcharge": bcharge,
        "timeleft": timeleft,
        "linev": linev,
        "battv": battv,
        "lotrans": lotrans,
        "hitrans": hitrans,
        "minlinev": minlinev,
        "maxlinev": maxlinev,
        "tonbatt": tonbatt,
        "cumonbatt": cumonbatt,
        "numxfers": numxfers,
        "battdate": battdate,
        "battery_age_years": battery_age_years,
        "conclusions": conclusions,
        "raw_fields": f,
    }


def _format_single_device_summary(derived: Dict[str, Any]) -> str:
    device = derived["device"]

    bits: List[str] = []
    if derived["on_battery"]:
        bits.append("on battery")
    else:
        bits.append("on mains power")

    if derived["loadpct"] is not None:
        bits.append(f"load {derived['loadpct']:.1f}%")

    if derived["bcharge"] is not None:
        bits.append(f"battery {derived['bcharge']:.1f}%")

    if derived["timeleft"] is not None:
        bits.append(f"estimated runtime {derived['timeleft']:.1f} min")

    if derived["linev"] is not None:
        bits.append(f"input {derived['linev']:.1f}V")

    sentence = f"{device}: " + ", ".join(bits) + "."

    notes = []
    if derived["low_battery"]:
        notes.append("low battery")
    if derived["overloaded"]:
        notes.append("high load")
    if derived["replace_battery"]:
        notes.append("replace battery")
    if derived["line_out_of_range"]:
        notes.append("input voltage outside window")
    if derived.get("battery_age_years") is not None and derived["battery_age_years"] >= 4:
        notes.append(f"battery age {derived['battery_age_years']:.1f} years")

    if notes:
        sentence += " Attention: " + ", ".join(notes) + "."

    return sentence




def _format_multi_device_summary(devices: List[Dict[str, Any]]) -> str:
    parts = [_format_single_device_summary(d) for d in devices]

    if len(devices) >= 2:
        sorted_runtime = sorted(
            [d for d in devices if d["timeleft"] is not None],
            key=lambda x: x["timeleft"]
        )
        if sorted_runtime:
            weakest = sorted_runtime[0]
            parts.append(
                f"The weakest runtime reserve is on {weakest['device']} "
                f"with {weakest['timeleft']:.1f} minutes remaining."
            )

        sorted_load = sorted(
            [d for d in devices if d["loadpct"] is not None],
            key=lambda x: x["loadpct"],
            reverse=True
        )
        if sorted_load:
            highest = sorted_load[0]
            parts.append(
                f"The highest load is on {highest['device']} "
                f"at {highest['loadpct']:.1f}%."
            )

    return " ".join(parts)


def detect_apc_intent(question: str) -> bool:
    q = question.lower()
    keywords = [
        "apc",
        "ups",
        "battery backup",
        "backup power",
        "power outage",
        "on battery",
        "running on battery",
        "mains power",
        "line voltage",
        "input voltage",
        "runtime",
        "battery health",
        "battery condition",
        "battery status",
        "load percentage",
        "highest load",
        "lowest runtime",
        "power fail",
        "transfer event",
    ]
    return any(k in q for k in keywords)




def handle_apc_question(
    question: str,
    query_api,
    org: str,
    bucket: str = APC_BUCKET_DEFAULT,
    measurements: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Main entry point for app.py.
    Returns None if the question is not APC-related.
    """
    if not detect_apc_intent(question):
        return None

    q = question.lower()

    snapshots = query_latest_apc_snapshot(
        query_api=query_api,
        org=org,
        bucket=bucket,
        measurements=measurements or APC_MEASUREMENTS_DEFAULT,
    )

    if not snapshots:
        return {
            "answer": "I could not find any APC UPS data in InfluxDB.",
            "intents": ["apc_summary"],
            "tool_data": {"apc_summary": {"devices": []}},
        }

    derived_devices = [_derive_apc_conclusions(s) for s in snapshots]

    # -------- question-specific responses --------

    # Is UPS on battery?
    if "on battery" in q or "running on battery" in q or "is my ups on battery" in q:
        on_batt = [d for d in derived_devices if d["on_battery"]]
        if on_batt:
            names = ", ".join(d["device"] for d in on_batt)
            answer = f"Yes. These UPS units are currently on battery: {names}."
        else:
            if len(derived_devices) == 1:
                answer = f"No. {derived_devices[0]['device']} is currently on mains power."
            else:
                answer = "No. All detected APC UPS units are currently on mains power."

        return {
            "answer": answer,
            "intents": ["apc_on_battery_status"],
            "tool_data": {
                "apc_on_battery_status": {
                    "device_count": len(derived_devices),
                    "devices": derived_devices,
                    "on_battery_count": len(on_batt),
                }
            },
        }

    # Highest load
    if "highest load" in q or "most load" in q or "highest usage" in q or "most heavily loaded" in q:
        candidates = [d for d in derived_devices if d["loadpct"] is not None]
        if candidates:
            highest = max(candidates, key=lambda d: d["loadpct"])
            answer = (
                f"The APC UPS with the highest load is {highest['device']} "
                f"at {highest['loadpct']:.1f}% load."
            )
        else:
            answer = "I could not determine APC load percentages from the available UPS data."

        return {
            "answer": answer,
            "intents": ["apc_highest_load"],
            "tool_data": {
                "apc_highest_load": {
                    "device_count": len(derived_devices),
                    "devices": derived_devices,
                    "highest_load_device": highest if candidates else None,
                }
            },
        }

    # Battery health / age
    if "battery health" in q or "battery condition" in q or "battery status" in q or "healthy is my ups battery" in q or "health of my ups battery" in q:
        parts = []
        for d in derived_devices:
            seg = f"{d['device']}: battery charge {d['bcharge']:.1f}%"
            if d["timeleft"] is not None:
                seg += f", estimated runtime {d['timeleft']:.1f} minutes"
            if d["battery_age_years"] is not None:
                seg += f", battery age {d['battery_age_years']:.1f} years"
            if d["replace_battery"]:
                seg += ", replace-battery warning is active"
            elif d["battery_age_years"] is not None and d["battery_age_years"] >= 4:
                seg += ", battery should be reviewed due to age"
            parts.append(seg + ".")

        answer = " ".join(parts)

        return {
            "answer": answer,
            "intents": ["apc_battery_health"],
            "tool_data": {
                "apc_battery_health": {
                    "device_count": len(derived_devices),
                    "devices": derived_devices,
                }
            },
        }

    # Lowest runtime
    if "lowest runtime" in q or "least runtime" in q or "shortest runtime" in q or "weakest runtime" in q:
        candidates = [d for d in derived_devices if d["timeleft"] is not None]
        if candidates:
            weakest = min(candidates, key=lambda d: d["timeleft"])
            answer = (
                f"The APC UPS with the shortest estimated runtime is {weakest['device']} "
                f"with {weakest['timeleft']:.1f} minutes remaining at the current load."
            )
        else:
            answer = "I could not determine APC runtime from the available UPS data."

        return {
            "answer": answer,
            "intents": ["apc_lowest_runtime"],
            "tool_data": {
                "apc_lowest_runtime": {
                    "device_count": len(derived_devices),
                    "devices": derived_devices,
                    "lowest_runtime_device": weakest if candidates else None,
                }
            },
        }

    # Voltage state
    if "line voltage" in q or "input voltage" in q or "voltage stable" in q or "voltage unstable" in q:
        parts = []
        for d in derived_devices:
            if d["linev"] is None:
                parts.append(f"{d['device']}: no input voltage reading available.")
            elif d["line_out_of_range"]:
                parts.append(
                    f"{d['device']}: input voltage is {d['linev']:.1f}V, outside the transfer window."
                )
            else:
                parts.append(
                    f"{d['device']}: input voltage is {d['linev']:.1f}V and within the transfer window."
                )

        return {
            "answer": " ".join(parts),
            "intents": ["apc_voltage_status"],
            "tool_data": {
                "apc_voltage_status": {
                    "device_count": len(derived_devices),
                    "devices": derived_devices,
                }
            },
        }

    # Generic summary fallback
    answer = _format_multi_device_summary(derived_devices)

    return {
        "answer": answer,
        "intents": ["apc_summary"],
        "tool_data": {
            "apc_summary": {
                "device_count": len(derived_devices),
                "devices": derived_devices,
            }
        },
    }
