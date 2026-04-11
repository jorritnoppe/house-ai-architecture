from datetime import datetime
from typing import Optional


class SMATools:
    def __init__(
        self,
        query_api,
        bucket: str = "sma_inverter",
        measurement: str = "sma_inverter",
        ac_power_field: str = "ac_power",
        daily_energy_field: str = "daily_energy",
        grid_voltage_field: str = "grid_current",
        inverter_temp_field: str = "inverter_temp",
        pv_current_field: str = "pv_current",
        pv_voltage_field: str = "pv_voltage",
        total_energy_field: str = "total_energy",
        daily_energy_divisor: float = 1000.0,
        total_energy_divisor: float = 1000.0,
        pv_voltage_divisor: float = 10.0,
        inverter_temp_divisor: float = 100.0,
    ):
        self.query_api = query_api
        self.bucket = bucket
        self.measurement = measurement

        self.ac_power_field = ac_power_field
        self.daily_energy_field = daily_energy_field
        self.grid_voltage_field = grid_voltage_field
        self.inverter_temp_field = inverter_temp_field
        self.pv_current_field = pv_current_field
        self.pv_voltage_field = pv_voltage_field
        self.total_energy_field = total_energy_field

        self.daily_energy_divisor = daily_energy_divisor
        self.total_energy_divisor = total_energy_divisor
        self.pv_voltage_divisor = pv_voltage_divisor
        self.inverter_temp_divisor = inverter_temp_divisor

    def _query_latest_fields(self, fields, range_window: str = "-30d"):
        if not fields:
            return {}

        field_filter = " or ".join([f'r._field == "{f}"' for f in fields])

        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{self.measurement}")
  |> filter(fn: (r) => {field_filter})
  |> last()
'''

        tables = self.query_api.query(flux)
        result = {f: None for f in fields}

        for table in tables:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                time_ = record.get_time()

                result[field] = {
                    "field": field,
                    "measurement": record.get_measurement(),
                    "value": float(value) if value is not None else None,
                    "time": time_.isoformat() if isinstance(time_, datetime) else str(time_),
                }

        return result

    @staticmethod
    def _safe_div(value: Optional[float], divisor: float) -> Optional[float]:
        if value is None:
            return None
        if divisor == 0:
            return None
        return value / divisor

    @staticmethod
    def _round_or_none(value: Optional[float], digits: int = 3) -> Optional[float]:
        if value is None:
            return None
        return round(value, digits)

    def get_summary(self):
        fields = [
            self.ac_power_field,
            self.daily_energy_field,
            self.grid_voltage_field,
            self.inverter_temp_field,
            self.pv_current_field,
            self.pv_voltage_field,
            self.total_energy_field,
        ]

        raw = self._query_latest_fields(fields, range_window="-30d")

        ac_power_w = raw.get(self.ac_power_field, {}).get("value") if raw.get(self.ac_power_field) else None
        daily_energy_raw = raw.get(self.daily_energy_field, {}).get("value") if raw.get(self.daily_energy_field) else None
        grid_voltage_v = raw.get(self.grid_voltage_field, {}).get("value") if raw.get(self.grid_voltage_field) else None
        inverter_temp_raw = raw.get(self.inverter_temp_field, {}).get("value") if raw.get(self.inverter_temp_field) else None
        pv_current_a = raw.get(self.pv_current_field, {}).get("value") if raw.get(self.pv_current_field) else None
        pv_voltage_raw = raw.get(self.pv_voltage_field, {}).get("value") if raw.get(self.pv_voltage_field) else None
        total_energy_raw = raw.get(self.total_energy_field, {}).get("value") if raw.get(self.total_energy_field) else None

        daily_energy_kwh = self._safe_div(daily_energy_raw, self.daily_energy_divisor)
        total_energy_kwh = self._safe_div(total_energy_raw, self.total_energy_divisor)
        pv_voltage_v = self._safe_div(pv_voltage_raw, self.pv_voltage_divisor)
        inverter_temp_c = self._safe_div(inverter_temp_raw, self.inverter_temp_divisor)

        timestamps = []
        for item in raw.values():
            if item and item.get("time"):
                timestamps.append(item["time"])
        latest_time = max(timestamps) if timestamps else None

        return {
            "status": "ok",
            "timestamp": latest_time,
            "source": {
                "bucket": self.bucket,
                "measurement": self.measurement,
            },
            "ac_power_w": self._round_or_none(ac_power_w, 3),
            "ac_power_kw": self._round_or_none(self._safe_div(ac_power_w, 1000.0), 3),
            "daily_energy_raw": self._round_or_none(daily_energy_raw, 3),
            "daily_energy_kwh": self._round_or_none(daily_energy_kwh, 3),
            "grid_voltage_v": self._round_or_none(grid_voltage_v, 3),
            "inverter_temp_raw": self._round_or_none(inverter_temp_raw, 3),
            "inverter_temp_c": self._round_or_none(inverter_temp_c, 3),
            "pv_current_a": self._round_or_none(pv_current_a, 3),
            "pv_voltage_raw": self._round_or_none(pv_voltage_raw, 3),
            "pv_voltage_v": self._round_or_none(pv_voltage_v, 3),
            "total_energy_raw": self._round_or_none(total_energy_raw, 3),
            "total_energy_kwh": self._round_or_none(total_energy_kwh, 3),
            "raw_fields": {
                "ac_power_field": self.ac_power_field,
                "daily_energy_field": self.daily_energy_field,
                "grid_voltage_field": self.grid_voltage_field,
                "inverter_temp_field": self.inverter_temp_field,
                "pv_current_field": self.pv_current_field,
                "pv_voltage_field": self.pv_voltage_field,
                "total_energy_field": self.total_energy_field,
            },
            "scaling": {
                "daily_energy_divisor": self.daily_energy_divisor,
                "total_energy_divisor": self.total_energy_divisor,
                "pv_voltage_divisor": self.pv_voltage_divisor,
                "inverter_temp_divisor": self.inverter_temp_divisor,
            },
        }

    def get_production_overview(self):
        s = self.get_summary()

        return {
            "status": s["status"],
            "timestamp": s["timestamp"],
            "ac_power_w": s["ac_power_w"],
            "ac_power_kw": s["ac_power_kw"],
            "daily_energy_kwh": s["daily_energy_kwh"],
            "total_energy_kwh": s["total_energy_kwh"],
            "pv_current_a": s["pv_current_a"],
            "pv_voltage_v": s["pv_voltage_v"],
            "grid_voltage_v": s["grid_voltage_v"],
            "inverter_temp_c": s["inverter_temp_c"],
            "inverter_temp_raw": s["inverter_temp_raw"],
            "source": s["source"],
            "raw_fields": s["raw_fields"],
            "scaling": s["scaling"],
        }
