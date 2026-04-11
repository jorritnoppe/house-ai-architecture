import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from influxdb_client import InfluxDBClient


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _to_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on", "active"):
        return True
    if s in ("false", "0", "no", "off", "inactive"):
        return False
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class BuderusService:
    """
    Reads Buderus EMS / boiler data already stored in InfluxDB.
    Assumes one measurement with many fields.
    """

    DEFAULT_FIELD_CANDIDATES = {
        "outside_temp": ["outside_temperature"],
        "flow_temp": ["set_flow_temperature", "flow_temperature"],
        "return_temp": ["return_temperature"],
        "summe_temp": ["summe_temperature"],
        "tapwater_active": ["tapwater_active"],
        "heating_active": ["heating_active"],
        "heating_pump": ["heating_pump"],
        "burner_power": [
            "burner_current_power",
            "normal_power",
            "dhw_set_pump_power",
            "selected_flow_temperature",
        ],
        "system_pressure": ["system_pressure"],
        "flame_current": ["flame_current"],
        "fan": ["fan"],
        "gas": ["gas"],
        "ignition": ["ignition"],
        "service_code": ["service_code"],
        "service_code_number": ["service_code_number"],
        "last_error_code": ["last_error_code"],
        "maintenance_message": ["maintenance_message"],
        "maintenance_scheduled": ["maintenance_scheduled"],
        "burner_starts": ["burner_starts"],
        "burner_starts_heating": ["burner_starts_heating"],
        "burner_in_period": ["burner_in_period"],
        "burner_up_period": ["burner_up_period"],
        "total_burner_operation": ["total_burner_operating_time"],
        "total_heat_operating": ["total_heat_operating_time"],
        "total_uba_operating": ["total_uba_operating_time"],
        "dhw_temp": [
            "dhw_current_tap_water_temperature",
            "dhw_storage_intern_temperature",
            "dhw_current_intern_temperature",
        ],
        "dhw_set_temp": ["dhw_set_temperature"],
        "heating_temp": ["heating_temperature"],
        "heating_curve_on": ["heatingcurve_on"],
        "heating_curve_base": ["heatingcurve_base"],
        "heating_curve_end": ["heatingcurve_end"],
        "nofrost_mode": ["nofrost_mode"],
        "nofrost_temperature": ["nofrost_temperature"],
        "pump_delay": ["pump_delay"],
        "oil_preheating": ["oil_preheating"],
        "energy_heating": ["energy_heating"],
    }

    def __init__(
        self,
        influx_url: str,
        influx_token: str,
        influx_org: str,
        bucket: str = "Buderus",
        measurement: str = "Buderus",
    ) -> None:
        self.influx_url = influx_url
        self.influx_token = influx_token
        self.influx_org = influx_org
        self.bucket = bucket
        self.measurement = measurement

        self.client = InfluxDBClient(
            url=self.influx_url,
            token=self.influx_token,
            org=self.influx_org,
            timeout=30000,
        )
        self.query_api = self.client.query_api()

    def _flux(self, query: str):
        return self.query_api.query(org=self.influx_org, query=query)

    def ping(self) -> Dict[str, Any]:
        try:
            health = self.client.health()
            return {
                "ok": health.status == "pass",
                "status": health.status,
                "message": getattr(health, "message", None),
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": "error",
                "message": str(exc),
            }

    def get_available_fields(self, hours: int = 168) -> List[str]:
        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
  |> keep(columns: ["_field"])
  |> group()
  |> distinct(column: "_field")
  |> sort(columns: ["_field"])
"""
        tables = self._flux(flux)
        fields = []
        for table in tables:
            for record in table.records:
                field = record.get_value()
                if field:
                    fields.append(str(field))
        return sorted(set(fields))

    def get_latest_fields(self, lookback_hours: int = 72) -> Dict[str, Dict[str, Any]]:
        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{lookback_hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
  |> group(columns: ["_field"])
  |> last()
  |> keep(columns: ["_time", "_field", "_value"])
"""
        tables = self._flux(flux)
        result: Dict[str, Dict[str, Any]] = {}
        for table in tables:
            for record in table.records:
                result[str(record["_field"])] = {
                    "value": record["_value"],
                    "time": _iso(record["_time"]),
                }
        return result

    def get_field_latest(self, field: str, lookback_hours: int = 168) -> Dict[str, Any]:
        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{lookback_hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}" and r["_field"] == "{field}")
  |> last()
"""
        tables = self._flux(flux)
        for table in tables:
            for record in table.records:
                return {
                    "field": field,
                    "value": record["_value"],
                    "time": _iso(record["_time"]),
                }
        return {"field": field, "value": None, "time": None}

    def get_field_stats(self, field: str, hours: int = 24) -> Dict[str, Any]:
        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}" and r["_field"] == "{field}")
  |> keep(columns: ["_time", "_value"])
"""

        tables = self._flux(flux)
        points = []

        for table in tables:
            for record in table.records:
                value = _to_float(record["_value"])
                if value is None:
                    continue

                points.append({
                    "time": _iso(record["_time"]),
                    "value": value
                })

        result = {
            "field": field,
            "range_hours": hours,
            "latest": None,
            "latest_time": None,
            "min": None,
            "min_time": None,
            "max": None,
            "max_time": None,
            "avg": None,
            "avg_time": None,
            "samples": len(points)
        }

        if not points:
            return result

        latest_point = points[-1]
        min_point = min(points, key=lambda x: x["value"])
        max_point = max(points, key=lambda x: x["value"])
        avg_value = sum(p["value"] for p in points) / len(points)

        result["latest"] = latest_point["value"]
        result["latest_time"] = latest_point["time"]
        result["min"] = min_point["value"]
        result["min_time"] = min_point["time"]
        result["max"] = max_point["value"]
        result["max_time"] = max_point["time"]
        result["avg"] = avg_value
        result["avg_time"] = latest_point["time"]

        return result

    def _counter_delta(self, field_name: str, hours: int = 24) -> Dict[str, Any]:
        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}" and r["_field"] == "{field_name}")
  |> keep(columns: ["_time", "_value"])
"""

        tables = self._flux(flux)
        points = []

        for table in tables:
            for record in table.records:
                value = _to_float(record["_value"])
                if value is None:
                    continue

                points.append({
                    "time": _iso(record["_time"]),
                    "value": value
                })

        result = {
            "field": field_name,
            "hours": hours,
            "first_value": None,
            "first_time": None,
            "last_value": None,
            "last_time": None,
            "delta": None,
            "samples": len(points)
        }

        if not points:
            return result

        first_point = points[0]
        last_point = points[-1]

        result["first_value"] = first_point["value"]
        result["first_time"] = first_point["time"]
        result["last_value"] = last_point["value"]
        result["last_time"] = last_point["time"]
        result["delta"] = last_point["value"] - first_point["value"]

        return result

    def compare_windows(self, field: str, hours: int = 24) -> Dict[str, Any]:
        current_stats = self.get_field_stats(field, hours=hours)

        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{hours * 2}h, stop: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}" and r["_field"] == "{field}")
  |> keep(columns: ["_time", "_value"])
"""
        tables = self._flux(flux)

        previous_points = []
        for table in tables:
            for record in table.records:
                value = _to_float(record["_value"])
                if value is None:
                    continue
                previous_points.append(value)

        previous_avg = None
        if previous_points:
            previous_avg = sum(previous_points) / len(previous_points)

        out = {
            "field": field,
            "hours": hours,
            "current_avg": current_stats.get("avg"),
            "previous_avg": previous_avg,
            "delta": None,
            "trend": "unknown",
        }

        if out["current_avg"] is not None and out["previous_avg"] is not None:
            out["delta"] = out["current_avg"] - out["previous_avg"]
            if out["delta"] > 0:
                out["trend"] = "higher"
            elif out["delta"] < 0:
                out["trend"] = "lower"
            else:
                out["trend"] = "equal"

        return out

    def _pick_value(self, latest: Dict[str, Dict[str, Any]], logical_name: str) -> Dict[str, Any]:
        for field in self.DEFAULT_FIELD_CANDIDATES.get(logical_name, []):
            if field in latest:
                return {
                    "field": field,
                    "value": latest[field]["value"],
                    "time": latest[field]["time"],
                }
        return {"field": None, "value": None, "time": None}

    def current_summary(self) -> Dict[str, Any]:
        latest = self.get_latest_fields()

        outside = self._pick_value(latest, "outside_temp")
        flow = self._pick_value(latest, "flow_temp")
        ret = self._pick_value(latest, "return_temp")
        dhw = self._pick_value(latest, "dhw_temp")
        pressure = self._pick_value(latest, "system_pressure")
        burner_power = self._pick_value(latest, "burner_power")
        flame_current = self._pick_value(latest, "flame_current")
        heating_active = self._pick_value(latest, "heating_active")
        tapwater_active = self._pick_value(latest, "tapwater_active")
        gas = self._pick_value(latest, "gas")
        ignition = self._pick_value(latest, "ignition")
        fan = self._pick_value(latest, "fan")
        error_code = self._pick_value(latest, "last_error_code")
        maintenance_message = self._pick_value(latest, "maintenance_message")

        heating_active_bool = _to_bool(heating_active["value"])
        tapwater_active_bool = _to_bool(tapwater_active["value"])
        gas_bool = _to_bool(gas["value"])
        ignition_bool = _to_bool(ignition["value"])

        burner_on = False
        bp = _to_float(burner_power["value"])
        fc = _to_float(flame_current["value"])

        if gas_bool is True or ignition_bool is True:
            burner_on = True
        if bp is not None and bp > 0:
            burner_on = True
        if fc is not None and fc > 0:
            burner_on = True

        operating_mode = "idle"
        if tapwater_active_bool:
            operating_mode = "hot_water"
        elif heating_active_bool:
            operating_mode = "heating"
        elif burner_on:
            operating_mode = "burner_on"

        return {
            "bucket": self.bucket,
            "measurement": self.measurement,
            "operating_mode": operating_mode,
            "burner_on": burner_on,
            "heating_active": heating_active_bool,
            "tapwater_active": tapwater_active_bool,
            "outside_temperature": outside,
            "flow_temperature": flow,
            "return_temperature": ret,
            "dhw_temperature": dhw,
            "system_pressure": pressure,
            "burner_power": burner_power,
            "flame_current": flame_current,
            "fan": fan,
            "last_error_code": error_code,
            "maintenance_message": maintenance_message,
            "observed_at": max(
                [x["time"] for x in latest.values() if x.get("time")] or [None]
            ),
        }

    def heating_summary(self) -> Dict[str, Any]:
        current = self.current_summary()

        return {
            "mode": "heating",
            "active": current["heating_active"],
            "burner_on": current["burner_on"],
            "outside_temperature_now": current["outside_temperature"],
            "flow_temperature_now": current["flow_temperature"],
            "return_temperature_now": current["return_temperature"],
            "system_pressure": current["system_pressure"],
            "heating_temperature_24h": self.get_field_stats("heating_temperature", hours=24),
            "set_flow_temperature_24h": self.get_field_stats("set_flow_temperature", hours=24),
            "return_temperature_24h": self.get_field_stats("return_temperature", hours=24)
        }

    def dhw_summary(self) -> Dict[str, Any]:
        current = self.current_summary()
        dhw_current = self._pick_value(self.get_latest_fields(), "dhw_temp")
        dhw_set = self._pick_value(self.get_latest_fields(), "dhw_set_temp")

        return {
            "mode": "hot_water",
            "active": current["tapwater_active"],
            "burner_on": current["burner_on"],
            "dhw_current_temperature": dhw_current,
            "dhw_set_temperature": dhw_set,
            "system_pressure": current["system_pressure"],
        }

    def burner_summary(self) -> Dict[str, Any]:
        current = self.current_summary()
        latest = self.get_latest_fields()

        starts = self._pick_value(latest, "burner_starts")
        starts_heating = self._pick_value(latest, "burner_starts_heating")
        in_period = self._pick_value(latest, "burner_in_period")
        up_period = self._pick_value(latest, "burner_up_period")
        total_burner_operation = self._pick_value(latest, "total_burner_operation")
        total_heat_operating = self._pick_value(latest, "total_heat_operating")
        total_uba_operating = self._pick_value(latest, "total_uba_operating")

        return {
            "burner_on": current["burner_on"],
            "burner_power": current["burner_power"],
            "flame_current": current["flame_current"],
            "burner_starts": starts,
            "burner_starts_heating": starts_heating,
            "burner_in_period": in_period,
            "burner_up_period": up_period,
            "total_burner_operation": total_burner_operation,
            "total_heat_operating_time": total_heat_operating,
            "total_uba_operating_time": total_uba_operating,
        }

    def diagnostics_summary(self) -> Dict[str, Any]:
        latest = self.get_latest_fields()
        service_code = self._pick_value(latest, "service_code")
        service_code_number = self._pick_value(latest, "service_code_number")
        last_error_code = self._pick_value(latest, "last_error_code")
        maintenance_message = self._pick_value(latest, "maintenance_message")
        maintenance_scheduled = self._pick_value(latest, "maintenance_scheduled")

        return {
            "service_code": service_code,
            "service_code_number": service_code_number,
            "last_error_code": last_error_code,
            "maintenance_message": maintenance_message,
            "maintenance_scheduled": maintenance_scheduled,
        }

    def pressure_analysis(self) -> Dict[str, Any]:
        latest = self.get_field_latest("system_pressure", lookback_hours=168)
        pressure = _to_float(latest.get("value"))

        status = "unknown"
        recommendation = "No recommendation available."

        if pressure is not None:
            if pressure < 1.0:
                status = "low"
                recommendation = "System pressure appears low. Check whether the heating circuit needs refilling."
            elif pressure < 1.2:
                status = "slightly_low"
                recommendation = "System pressure is slightly low but may still be acceptable depending on your system."
            elif pressure <= 2.2:
                status = "normal"
                recommendation = "System pressure looks normal."
            elif pressure <= 2.8:
                status = "slightly_high"
                recommendation = "System pressure is somewhat high. Monitor it, especially during heating cycles."
            else:
                status = "high"
                recommendation = "System pressure appears high. Check filling pressure, expansion vessel condition, or relief valve behavior."

        return {
            "field": "system_pressure",
            "latest": latest,
            "status": status,
            "recommendation": recommendation
        }

    def fault_history_analysis(self, hours: int = 168) -> Dict[str, Any]:
        last_error = self.get_field_latest("last_error_code", lookback_hours=hours)
        maintenance_message = self.get_field_latest("maintenance_message", lookback_hours=hours)
        maintenance_scheduled = self.get_field_latest("maintenance_scheduled", lookback_hours=hours)
        service_code = self.get_field_latest("service_code", lookback_hours=hours)
        service_code_number = self.get_field_latest("service_code_number", lookback_hours=hours)

        error_value = _to_float(last_error.get("value"))
        maintenance_value = _to_float(maintenance_message.get("value"))

        status = "ok"
        if error_value is not None and error_value != 0:
            status = "fault_present"
        elif maintenance_value is not None and maintenance_value != 0:
            status = "maintenance_present"

        return {
            "hours": hours,
            "status": status,
            "last_error_code": last_error,
            "maintenance_message": maintenance_message,
            "maintenance_scheduled": maintenance_scheduled,
            "service_code": service_code,
            "service_code_number": service_code_number
        }

    def burner_starts_analysis(self, hours: int = 24) -> Dict[str, Any]:
        burner_starts = self._counter_delta("burner_starts", hours=hours)
        burner_starts_heating = self._counter_delta("burner_starts_heating", hours=hours)
        dhw_starts = self._counter_delta("dhw_starts", hours=hours)

        return {
            "hours": hours,
            "burner_starts": burner_starts,
            "burner_starts_heating": burner_starts_heating,
            "dhw_starts": dhw_starts
        }



    def _count_true_samples(self, field_name: str, hours: int = 24) -> Dict[str, Any]:
        flux = f"""
from(bucket: "{self.bucket}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "{self.measurement}" and r["_field"] == "{field_name}")
  |> keep(columns: ["_time", "_value"])
"""

        tables = self._flux(flux)
        true_count = 0
        false_count = 0
        total = 0

        for table in tables:
            for record in table.records:
                b = _to_bool(record["_value"])
                if b is None:
                    continue

                total += 1
                if b:
                    true_count += 1
                else:
                    false_count += 1

        ratio_true = None
        if total > 0:
            ratio_true = true_count / total

        return {
            "field": field_name,
            "hours": hours,
            "samples": total,
            "true_samples": true_count,
            "false_samples": false_count,
            "true_ratio": ratio_true
        }


    def operating_time_analysis(self, hours: int = 24) -> Dict[str, Any]:
        burner_operating = self._counter_delta("total_burner_operating_time", hours=hours)
        heat_operating = self._counter_delta("total_heat_operating_time", hours=hours)
        uba_operating = self._counter_delta("total_uba_operating_time", hours=hours)

        return {
            "hours": hours,
            "total_burner_operating_time": burner_operating,
            "total_heat_operating_time": heat_operating,
            "total_uba_operating_time": uba_operating
        }


    def heating_vs_dhw_analysis(self, hours: int = 24) -> Dict[str, Any]:
        heating_active = self._count_true_samples("heating_active", hours=hours)
        tapwater_active = self._count_true_samples("tapwater_active", hours=hours)

        return {
            "hours": hours,
            "heating_active": heating_active,
            "tapwater_active": tapwater_active
        }


    def temperature_delta_analysis(self, hours: int = 24) -> Dict[str, Any]:
        flow_latest = self.get_field_latest("set_flow_temperature", lookback_hours=hours)
        return_latest = self.get_field_latest("return_temperature", lookback_hours=hours)
        outside_latest = self.get_field_latest("outside_temperature", lookback_hours=hours)
        dhw_latest = self.get_field_latest("dhw_storage_intern_temperature", lookback_hours=hours)

        flow = _to_float(flow_latest.get("value"))
        ret = _to_float(return_latest.get("value"))
        outside = _to_float(outside_latest.get("value"))
        dhw = _to_float(dhw_latest.get("value"))

        flow_return_delta = None
        flow_outside_delta = None
        dhw_outside_delta = None

        if flow is not None and ret is not None:
            flow_return_delta = flow - ret

        if flow is not None and outside is not None:
            flow_outside_delta = flow - outside

        if dhw is not None and outside is not None:
            dhw_outside_delta = dhw - outside

        return {
            "hours": hours,
            "flow_temperature": flow_latest,
            "return_temperature": return_latest,
            "outside_temperature": outside_latest,
            "dhw_storage_intern_temperature": dhw_latest,
            "flow_return_delta": flow_return_delta,
            "flow_outside_delta": flow_outside_delta,
            "dhw_outside_delta": dhw_outside_delta
        }


    def short_cycling_analysis(self, hours: int = 24) -> Dict[str, Any]:
        starts_delta = self._counter_delta("burner_starts", hours=hours)
        burner_time_delta = self._counter_delta("total_burner_operating_time", hours=hours)

        starts = _to_float(starts_delta.get("delta"))
        burner_minutes = _to_float(burner_time_delta.get("delta"))

        avg_minutes_per_start = None
        status = "unknown"
        recommendation = "Not enough data."

        if starts is not None and burner_minutes is not None and starts > 0:
            avg_minutes_per_start = burner_minutes / starts

            if avg_minutes_per_start < 3:
                status = "likely_short_cycling"
                recommendation = "Average burner runtime per start is very low. This suggests possible short cycling."
            elif avg_minutes_per_start < 6:
                status = "borderline"
                recommendation = "Average burner runtime per start is somewhat low. Monitor for short cycling."
            else:
                status = "normal"
                recommendation = "Average burner runtime per start looks reasonable."

        return {
            "hours": hours,
            "burner_starts_delta": starts_delta,
            "total_burner_operating_time_delta": burner_time_delta,
            "avg_minutes_per_start": avg_minutes_per_start,
            "status": status,
            "recommendation": recommendation
        }


    def heating_curve_analysis(self) -> Dict[str, Any]:
        latest = self.get_latest_fields()

        heatingcurve_on = self._pick_value(latest, "heating_curve_on")
        heatingcurve_base = self._pick_value(latest, "heating_curve_base")
        heatingcurve_end = self._pick_value(latest, "heating_curve_end")
        nofrost_mode = self._pick_value(latest, "nofrost_mode")
        nofrost_temperature = self._pick_value(latest, "nofrost_temperature")

        summer_temperature = self.get_field_latest("summer_temperature", lookback_hours=168)
        heating_temperature = self.get_field_latest("heating_temperature", lookback_hours=168)

        return {
            "heatingcurve_on": heatingcurve_on,
            "heatingcurve_base": heatingcurve_base,
            "heatingcurve_end": heatingcurve_end,
            "nofrost_mode": nofrost_mode,
            "nofrost_temperature": nofrost_temperature,
            "summer_temperature": summer_temperature,
            "heating_temperature": heating_temperature
        }


    def energy_analysis(self, hours: int = 24) -> Dict[str, Any]:
        energy_heating = self.get_field_stats("energy_heating", hours=hours)
        dhw_energy = self.get_field_stats("dhw_energy", hours=hours)
        total_energy = self.get_field_stats("total_energy", hours=hours)

        return {
            "hours": hours,
            "energy_heating": energy_heating,
            "dhw_energy": dhw_energy,
            "total_energy": total_energy
        }


    def compare_today_vs_yesterday(self, field: str) -> Dict[str, Any]:
        return self.compare_windows(field=field, hours=24)


    def boiler_health_summary(self) -> Dict[str, Any]:
        current = self.current_summary()
        pressure = self.pressure_analysis()
        faults = self.fault_history_analysis(hours=168)
        short_cycling = self.short_cycling_analysis(hours=24)
        heating_vs_dhw = self.heating_vs_dhw_analysis(hours=24)

        health_score = 100
        notes = []

        pressure_status = pressure.get("status")
        if pressure_status == "low":
            health_score -= 25
            notes.append("System pressure is low.")
        elif pressure_status == "slightly_low":
            health_score -= 10
            notes.append("System pressure is slightly low.")
        elif pressure_status == "slightly_high":
            health_score -= 10
            notes.append("System pressure is slightly high.")
        elif pressure_status == "high":
            health_score -= 25
            notes.append("System pressure is high.")

        fault_status = faults.get("status")
        if fault_status == "fault_present":
            health_score -= 35
            notes.append("A fault code is currently present.")
        elif fault_status == "maintenance_present":
            health_score -= 15
            notes.append("A maintenance message is currently present.")

        short_cycle_status = short_cycling.get("status")
        if short_cycle_status == "likely_short_cycling":
            health_score -= 20
            notes.append("Burner behavior suggests short cycling.")
        elif short_cycle_status == "borderline":
            health_score -= 10
            notes.append("Burner runtime per start is somewhat low.")

        burner_on = current.get("burner_on")
        heating_active = current.get("heating_active")
        tapwater_active = current.get("tapwater_active")

        if burner_on:
            notes.append("Burner is currently active.")
        if heating_active:
            notes.append("Space heating is currently active.")
        if tapwater_active:
            notes.append("Hot water production is currently active.")

        if health_score >= 90:
            status = "good"
        elif health_score >= 70:
            status = "watch"
        else:
            status = "attention"

        return {
            "status": status,
            "health_score": max(0, health_score),
            "notes": notes,
            "current": current,
            "pressure": pressure,
            "faults": faults,
            "short_cycling": short_cycling,
            "heating_vs_dhw": heating_vs_dhw
        }







    def build_natural_answer(self, payload: Dict[str, Any], intent: str) -> str:
        if intent == "buderus_current_status":
            mode = payload.get("operating_mode", "unknown")
            outside = payload.get("outside_temperature", {}).get("value")
            flow = payload.get("flow_temperature", {}).get("value")
            ret = payload.get("return_temperature", {}).get("value")
            pressure = payload.get("system_pressure", {}).get("value")
            burner_on = payload.get("burner_on")

            return (
                f"Buderus status: mode is {mode}, "
                f"burner is {'on' if burner_on else 'off'}, "
                f"outside temperature is {outside}, "
                f"flow temperature is {flow}, "
                f"return temperature is {ret}, "
                f"system pressure is {pressure}."
            )

        if intent == "buderus_heating_status":
            active = payload.get("active")
            burner_on = payload.get("burner_on")
            flow_now = payload.get("flow_temperature_now", {}).get("value")
            ret_now = payload.get("return_temperature_now", {}).get("value")
            outside_now = payload.get("outside_temperature_now", {}).get("value")
            pressure = payload.get("system_pressure", {}).get("value")

            return (
                f"Heating is {'active' if active else 'not active'}. "
                f"Burner is {'on' if burner_on else 'off'}. "
                f"Outside temperature is {outside_now}, "
                f"flow temperature is {flow_now}, "
                f"return temperature is {ret_now}, "
                f"and system pressure is {pressure}."
            )

        if intent == "buderus_hot_water_status":
            active = payload.get("active")
            dhw_now = payload.get("dhw_current_temperature", {}).get("value")
            dhw_set = payload.get("dhw_set_temperature", {}).get("value")
            return (
                f"Hot water is {'active' if active else 'not active'}. "
                f"Current DHW temperature is {dhw_now} and target DHW temperature is {dhw_set}."
            )

        if intent == "buderus_burner_status":
            burner_on = payload.get("burner_on")
            burner_power = payload.get("burner_power", {}).get("value")
            flame_current = payload.get("flame_current", {}).get("value")
            starts = payload.get("burner_starts", {}).get("value")
            return (
                f"Burner is {'on' if burner_on else 'off'}. "
                f"Burner power is {burner_power}, flame current is {flame_current}, "
                f"and burner starts counter is {starts}."
            )

        if intent == "buderus_diagnostics":
            err = payload.get("last_error_code", {}).get("value")
            svc = payload.get("service_code", {}).get("value")
            maint = payload.get("maintenance_message", {}).get("value")
            return (
                f"Diagnostics: last error code is {err}, service code is {svc}, "
                f"maintenance message is {maint}."
            )

        if intent == "buderus_pressure_analysis":
            pressure = payload.get("latest", {}).get("value")
            status = payload.get("status")
            recommendation = payload.get("recommendation")

            return (
                f"System pressure is {pressure} bar and looks {status}. "
                f"{recommendation}"
            )



        if intent == "buderus_fault_history":
            status = payload.get("status")
            last_error = payload.get("last_error_code", {}).get("value")
            maintenance_message = payload.get("maintenance_message", {}).get("value")
            service_code = payload.get("service_code", {}).get("value")
            service_code_number = payload.get("service_code_number", {}).get("value")

            return (
                f"Fault history status is {status}. "
                f"Last error code is {last_error}, "
                f"maintenance message is {maintenance_message}, "
                f"service code is {service_code}, "
                f"and service code number is {service_code_number}."
            )

        if intent == "buderus_burner_starts_analysis":
            burner_delta = payload.get("burner_starts", {}).get("delta")
            heating_delta = payload.get("burner_starts_heating", {}).get("delta")
            dhw_delta = payload.get("dhw_starts", {}).get("delta")

            return (
                f"In the last {payload.get('hours')} hours, "
                f"burner starts changed by {burner_delta}, "
                f"heating burner starts changed by {heating_delta}, "
                f"and DHW starts changed by {dhw_delta}."
            )

        if intent == "buderus_compare_field":
            field = payload.get("field")
            current_avg = payload.get("current_avg")
            previous_avg = payload.get("previous_avg")
            delta = payload.get("delta")
            trend = payload.get("trend")
            return (
                f"For {field}, the average over the last {payload.get('hours')} hours is {current_avg}. "
                f"In the previous window it was {previous_avg}. "
                f"That is {trend} by {delta}."
            )


        if intent == "buderus_operating_time_analysis":
            burner = payload.get("total_burner_operating_time", {}).get("delta")
            heat = payload.get("total_heat_operating_time", {}).get("delta")
            uba = payload.get("total_uba_operating_time", {}).get("delta")

            return (
                f"In the last {payload.get('hours')} hours, "
                f"burner operating time changed by {burner}, "
                f"heat operating time changed by {heat}, "
                f"and UBA operating time changed by {uba}."
            )

        if intent == "buderus_heating_vs_dhw":
            heating_ratio = payload.get("heating_active", {}).get("true_ratio")
            tapwater_ratio = payload.get("tapwater_active", {}).get("true_ratio")

            heating_pct = None if heating_ratio is None else round(heating_ratio * 100, 1)
            tapwater_pct = None if tapwater_ratio is None else round(tapwater_ratio * 100, 1)

            return (
                f"In the last {payload.get('hours')} hours, "
                f"heating was active about {heating_pct}% of the time, "
                f"and tap water was active about {tapwater_pct}% of the time."
            )


        if intent == "buderus_temperature_delta_analysis":
            flow_return_delta = payload.get("flow_return_delta")
            flow_outside_delta = payload.get("flow_outside_delta")
            dhw_outside_delta = payload.get("dhw_outside_delta")

            return (
                f"Current flow minus return temperature delta is {flow_return_delta}, "
                f"flow minus outside temperature delta is {flow_outside_delta}, "
                f"and DHW minus outside temperature delta is {dhw_outside_delta}."
            )

        if intent == "buderus_short_cycling":
            avg_minutes = payload.get("avg_minutes_per_start")
            status = payload.get("status")
            recommendation = payload.get("recommendation")

            if avg_minutes is not None:
                avg_minutes = round(avg_minutes, 2)

            return (
                f"Short cycling analysis status is {status}. "
                f"Average burner runtime per start is {avg_minutes} minutes. "
                f"{recommendation}"
            )


        if intent == "buderus_heating_curve_analysis":
            curve_on = payload.get("heatingcurve_on", {}).get("value")
            curve_base = payload.get("heatingcurve_base", {}).get("value")
            curve_end = payload.get("heatingcurve_end", {}).get("value")
            nofrost_mode = payload.get("nofrost_mode", {}).get("value")
            nofrost_temperature = payload.get("nofrost_temperature", {}).get("value")
            summer_temperature = payload.get("summer_temperature", {}).get("value")
            heating_temperature = payload.get("heating_temperature", {}).get("value")

            return (
                f"Heating curve is {'on' if _to_bool(curve_on) else 'off'}. "
                f"Curve base is {curve_base}, curve end is {curve_end}, "
                f"summer temperature is {summer_temperature}, "
                f"heating temperature is {heating_temperature}, "
                f"nofrost mode is {nofrost_mode}, "
                f"and nofrost temperature is {nofrost_temperature}."
            )

        if intent == "buderus_energy_analysis":
            heating_avg = payload.get("energy_heating", {}).get("avg")
            dhw_avg = payload.get("dhw_energy", {}).get("avg")
            total_avg = payload.get("total_energy", {}).get("avg")

            return (
                f"In the last {payload.get('hours')} hours, "
                f"average heating energy was {heating_avg}, "
                f"average DHW energy was {dhw_avg}, "
                f"and average total energy was {total_avg}."
            )

        if intent == "buderus_compare_today_vs_yesterday":
            field = payload.get("field")
            current_avg = payload.get("current_avg")
            previous_avg = payload.get("previous_avg")
            trend = payload.get("trend")
            delta = payload.get("delta")

            return (
                f"For {field}, today's average is {current_avg}, "
                f"yesterday's average is {previous_avg}, "
                f"so today is {trend} by {delta}."
            )

        if intent == "buderus_boiler_health_summary":
            status = payload.get("status")
            health_score = payload.get("health_score")
            notes = payload.get("notes", [])

            note_text = " ".join(notes) if notes else "No major issues detected."

            return (
                f"Boiler health summary: status is {status}, "
                f"health score is {health_score} out of 100. "
                f"{note_text}"
            )




        if intent == "buderus_available_fields":
            fields = payload.get("fields", [])
            return f"Buderus has {len(fields)} available fields in InfluxDB."

        return "Buderus data processed successfully."

    def handle_agent_question(self, question: str) -> Optional[Dict[str, Any]]:
        q = (question or "").strip().lower()
        if not q:
            return None

        if any(x in q for x in ["buderus status", "boiler status", "heating status now", "boiler now", "current buderus"]):
            data = self.current_summary()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_current_status"],
                "answer": self.build_natural_answer(data, "buderus_current_status"),
                "tool_data": {"buderus_current_status": data},
            }

        if any(x in q for x in ["heating active", "is heating running", "central heating", "radiator heating", "heating circuit"]):
            data = self.heating_summary()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_heating_status"],
                "answer": self.build_natural_answer(data, "buderus_heating_status"),
                "tool_data": {"buderus_heating_status": data},
            }



        if any(x in q for x in ["heating vs hot water", "heating vs dhw", "house heating or hot water", "heating or hot water"]):
            data = self.heating_vs_dhw_analysis(hours=24)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_heating_vs_dhw"],
                "answer": self.build_natural_answer(data, "buderus_heating_vs_dhw"),
                "tool_data": {
                    "buderus_heating_vs_dhw": data
                }
            }



        if any(x in q for x in ["hot water", "tap water", "dhw", "warm water"]):
            data = self.dhw_summary()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_hot_water_status"],
                "answer": self.build_natural_answer(data, "buderus_hot_water_status"),
                "tool_data": {"buderus_hot_water_status": data},
            }




        if any(x in q for x in ["fault history", "error history", "boiler faults", "faults last 7 days"]):
            data = self.fault_history_analysis(hours=168)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_fault_history"],
                "answer": self.build_natural_answer(data, "buderus_fault_history"),
                "tool_data": {
                    "buderus_fault_history": data
                }
            }

        if any(x in q for x in ["burner starts today", "burner starts", "how often did the burner start"]):
            data = self.burner_starts_analysis(hours=24)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_burner_starts_analysis"],
                "answer": self.build_natural_answer(data, "buderus_burner_starts_analysis"),
                "tool_data": {
                    "buderus_burner_starts_analysis": data
                }
            }



        if any(x in q for x in ["burner", "flame", "gas valve", "ignition"]):
            data = self.burner_summary()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_burner_status"],
                "answer": self.build_natural_answer(data, "buderus_burner_status"),
                "tool_data": {"buderus_burner_status": data},
            }

        if any(x in q for x in ["error code", "fault", "diagnostic", "service code", "maintenance"]):
            data = self.diagnostics_summary()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_diagnostics"],
                "answer": self.build_natural_answer(data, "buderus_diagnostics"),
                "tool_data": {"buderus_diagnostics": data},
            }

        if any(x in q for x in ["pressure", "system pressure", "boiler pressure"]):
            data = self.pressure_analysis()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_pressure_analysis"],
                "answer": self.build_natural_answer(data, "buderus_pressure_analysis"),
                "tool_data": {
                    "buderus_pressure_analysis": data
                }
            }


        compare_match = re.search(
            r"compare.*last\s+(\d+)\s*h.*(?:for|of)?\s*([a-zA-Z0-9_]+)",
            q
        )
        if compare_match:
            hours = int(compare_match.group(1))
            field = compare_match.group(2)
            data = self.compare_windows(field=field, hours=hours)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_compare_field"],
                "answer": self.build_natural_answer(data, "buderus_compare_field"),
                "tool_data": {"buderus_compare_field": data},
            }

        if "available buderus fields" in q or "list buderus fields" in q:
            fields = self.get_available_fields()
            data = {"fields": fields}
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_available_fields"],
                "answer": self.build_natural_answer(data, "buderus_available_fields"),
                "tool_data": {"buderus_available_fields": data},
            }


        if any(x in q for x in ["operating time", "burner operating time", "heat operating time"]):
            data = self.operating_time_analysis(hours=24)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_operating_time_analysis"],
                "answer": self.build_natural_answer(data, "buderus_operating_time_analysis"),
                "tool_data": {
                    "buderus_operating_time_analysis": data
                }
            }


        if any(x in q for x in ["temperature delta", "flow return delta", "delta between flow and return"]):
            data = self.temperature_delta_analysis(hours=24)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_temperature_delta_analysis"],
                "answer": self.build_natural_answer(data, "buderus_temperature_delta_analysis"),
                "tool_data": {
                    "buderus_temperature_delta_analysis": data
                }
            }

        if any(x in q for x in ["short cycling", "short cycle", "burner cycling too often"]):
            data = self.short_cycling_analysis(hours=24)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_short_cycling"],
                "answer": self.build_natural_answer(data, "buderus_short_cycling"),
                "tool_data": {
                    "buderus_short_cycling": data
                }
            }



        if any(x in q for x in ["heating curve", "curve settings", "nofrost", "summer temperature"]):
            data = self.heating_curve_analysis()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_heating_curve_analysis"],
                "answer": self.build_natural_answer(data, "buderus_heating_curve_analysis"),
                "tool_data": {
                    "buderus_heating_curve_analysis": data
                }
            }

        if any(x in q for x in ["energy analysis", "energy heating", "dhw energy", "boiler energy"]):
            data = self.energy_analysis(hours=24)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_energy_analysis"],
                "answer": self.build_natural_answer(data, "buderus_energy_analysis"),
                "tool_data": {
                    "buderus_energy_analysis": data
                }
            }

        compare_today_match = re.search(
            r"(compare today vs yesterday for|today vs yesterday for)\s+([a-zA-Z0-9_]+)",
            q
        )
        if compare_today_match:
            field = compare_today_match.group(2)
            data = self.compare_today_vs_yesterday(field)
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_compare_today_vs_yesterday"],
                "answer": self.build_natural_answer(data, "buderus_compare_today_vs_yesterday"),
                "tool_data": {
                    "buderus_compare_today_vs_yesterday": data
                }
            }

        if any(x in q for x in ["boiler health", "boiler health summary", "is the boiler healthy", "boiler summary"]):
            data = self.boiler_health_summary()
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["buderus_boiler_health_summary"],
                "answer": self.build_natural_answer(data, "buderus_boiler_health_summary"),
                "tool_data": {
                    "buderus_boiler_health_summary": data
                }
            }







        return None


def _make_blueprint(service: BuderusService) -> Blueprint:
    bp = Blueprint("buderus_module", __name__, url_prefix="/tools/buderus")

    @bp.route("/health", methods=["GET"])
    def buderus_health():
        return jsonify(service.ping())

    @bp.route("/available_fields", methods=["GET"])
    def available_fields():
        hours = int(request.args.get("hours", "168"))
        return jsonify({
            "status": "ok",
            "bucket": service.bucket,
            "measurement": service.measurement,
            "fields": service.get_available_fields(hours=hours),
        })

    @bp.route("/current", methods=["GET"])
    def current():
        return jsonify({
            "status": "ok",
            "data": service.current_summary(),
        })

    @bp.route("/heating", methods=["GET"])
    def heating():
        return jsonify({
            "status": "ok",
            "data": service.heating_summary(),
        })

    @bp.route("/dhw", methods=["GET"])
    def dhw():
        return jsonify({
            "status": "ok",
            "data": service.dhw_summary(),
        })

    @bp.route("/burner", methods=["GET"])
    def burner():
        return jsonify({
            "status": "ok",
            "data": service.burner_summary(),
        })

    @bp.route("/diagnostics", methods=["GET"])
    def diagnostics():
        return jsonify({
            "status": "ok",
            "data": service.diagnostics_summary(),
        })

    @bp.route("/pressure", methods=["GET"])
    def pressure():
        return jsonify({
            "status": "ok",
            "data": service.pressure_analysis()
        })

    @bp.route("/fault_history", methods=["GET"])
    def fault_history():
        hours = int(request.args.get("hours", "168"))
        return jsonify({
            "status": "ok",
            "data": service.fault_history_analysis(hours=hours)
        })

    @bp.route("/burner_starts", methods=["GET"])
    def burner_starts():
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.burner_starts_analysis(hours=hours)
        })

    @bp.route("/field/<field_name>", methods=["GET"])
    def field_latest(field_name: str):
        lookback_hours = int(request.args.get("lookback_hours", "168"))
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "latest": service.get_field_latest(field_name, lookback_hours=lookback_hours),
            "stats": service.get_field_stats(field_name, hours=hours),
        })

    @bp.route("/compare/<field_name>", methods=["GET"])
    def compare(field_name: str):
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.compare_windows(field_name, hours=hours),
        })

    @bp.route("/ask", methods=["POST"])
    def ask():
        body = request.get_json(silent=True) or {}
        question = body.get("question", "")
        answer = service.handle_agent_question(question)
        if answer is None:
            return jsonify({
                "status": "no_match",
                "message": "No Buderus routine matched this question.",
            }), 404
        return jsonify(answer)



    @bp.route("/operating_time", methods=["GET"])
    def operating_time():
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.operating_time_analysis(hours=hours)
        })

    @bp.route("/heating_vs_dhw", methods=["GET"])
    def heating_vs_dhw():
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.heating_vs_dhw_analysis(hours=hours)
        })

    @bp.route("/temperature_delta", methods=["GET"])
    def temperature_delta():
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.temperature_delta_analysis(hours=hours)
        })

    @bp.route("/short_cycling", methods=["GET"])
    def short_cycling():
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.short_cycling_analysis(hours=hours)
        })


    @bp.route("/heating_curve", methods=["GET"])
    def heating_curve():
        return jsonify({
            "status": "ok",
            "data": service.heating_curve_analysis()
        })

    @bp.route("/energy", methods=["GET"])
    def energy():
        hours = int(request.args.get("hours", "24"))
        return jsonify({
            "status": "ok",
            "data": service.energy_analysis(hours=hours)
        })

    @bp.route("/compare_today_vs_yesterday/<field_name>", methods=["GET"])
    def compare_today_vs_yesterday(field_name: str):
        return jsonify({
            "status": "ok",
            "data": service.compare_today_vs_yesterday(field_name)
        })

    @bp.route("/health_summary", methods=["GET"])
    def health_summary():
        return jsonify({
            "status": "ok",
            "data": service.boiler_health_summary()
        })




    return bp


def load_buderus_module(app) -> None:
    """
    One-line loader from app.py:
    from buderus_module import load_buderus_module; load_buderus_module(app)
    """

    influx_url = _env("BUDERUS_INFLUX_URL", _env("INFLUX_URL", "http://127.0.0.1:8086"))
    influx_token = _env("BUDERUS_INFLUX_TOKEN", _env("INFLUX_TOKEN"))
    influx_org = _env("BUDERUS_INFLUX_ORG", _env("INFLUX_ORG"))
    bucket = _env("BUDERUS_INFLUX_BUCKET", "Buderus")
    measurement = _env("BUDERUS_MEASUREMENT", "Buderus")

    if not influx_token or influx_token == "CHANGE_ME":
        raise RuntimeError("Missing valid BUDERUS_INFLUX_TOKEN or INFLUX_TOKEN")

    if not influx_org:
        raise RuntimeError("Missing BUDERUS_INFLUX_ORG or INFLUX_ORG")

    service = BuderusService(
        influx_url=influx_url,
        influx_token=influx_token,
        influx_org=influx_org,
        bucket=bucket,
        measurement=measurement,
    )

    app.register_blueprint(_make_blueprint(service))

    app.extensions = getattr(app, "extensions", {})
    app.extensions["buderus_service"] = service
