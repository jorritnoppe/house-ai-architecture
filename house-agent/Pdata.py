import os
from datetime import datetime
from typing import Any


class PdataTools:
    def __init__(self, query_api):
        self.query_api = query_api
        self.bucket = os.getenv("PDATA_INFLUX_BUCKET", "Pdata")
        self.measurement = os.getenv("PDATA_INFLUX_MEASUREMENT", "Pdata")

        self.known_obis = {
            "0_0:17_0_0": {
                "label": "max_demand_kw",
                "description": "Maximum demand",
                "unit": "kW",
                "category": "general",
            },
            "0_0:96_14_0": {
                "label": "tariff_indicator",
                "description": "Current tariff indicator",
                "unit": None,
                "category": "general",
            },
            "0_0:96_1_1": {
                "label": "meter_id",
                "description": "Electricity meter identifier",
                "unit": None,
                "category": "general",
            },
            "0_0:96_1_4": {
                "label": "version_info",
                "description": "Version or device information",
                "unit": None,
                "category": "general",
            },
            "0_0:96_3_10": {
                "label": "breaker_status",
                "description": "Breaker / switch status",
                "unit": None,
                "category": "general",
            },
            "0_0:98_1_0": {
                "label": "historical_register",
                "description": "Historical register",
                "unit": None,
                "category": "general",
            },
            "0_1:24_1_0": {
                "label": "gas_meter_id",
                "description": "Gas meter identifier",
                "unit": None,
                "category": "gas",
            },
            "0_1:24_2_1": {
                "label": "gas_delivered_m3",
                "description": "Gas delivered total",
                "unit": "m3",
                "category": "gas",
            },
            "0_1:24_2_3": {
                "label": "gas_delivered_m3_alt",
                "description": "Gas delivered total alternate register",
                "unit": "m3",
                "category": "gas",
            },
            "0_1:24_3_0": {
                "label": "gas_timestamp_or_register",
                "description": "Gas timestamp or gas register info",
                "unit": None,
                "category": "gas",
            },
            "0_1:24_4_0": {
                "label": "gas_valve_status",
                "description": "Gas valve or gas status",
                "unit": None,
                "category": "gas",
            },
            "1_0:1_4_0": {
                "label": "current_average_demand_kw",
                "description": "Current average demand",
                "unit": "kW",
                "category": "power",
            },
            "1_0:1_7_0": {
                "label": "current_import_kw",
                "description": "Current active power import",
                "unit": "kW",
                "category": "power",
            },
            "1_0:1_8_1": {
                "label": "import_t1_kwh",
                "description": "Imported energy tariff 1",
                "unit": "kWh",
                "category": "energy",
            },
            "1_0:1_8_2": {
                "label": "import_t2_kwh",
                "description": "Imported energy tariff 2",
                "unit": "kWh",
                "category": "energy",
            },
            "1_0:2_7_0": {
                "label": "current_export_kw",
                "description": "Current active power export",
                "unit": "kW",
                "category": "power",
            },
            "1_0:2_8_1": {
                "label": "export_t1_kwh",
                "description": "Exported energy tariff 1",
                "unit": "kWh",
                "category": "energy",
            },
            "1_0:2_8_2": {
                "label": "export_t2_kwh",
                "description": "Exported energy tariff 2",
                "unit": "kWh",
                "category": "energy",
            },
            "1_0:21_7_0": {
                "label": "l1_import_kw",
                "description": "Phase L1 active import power",
                "unit": "kW",
                "category": "phase_power",
            },
            "1_0:22_7_0": {
                "label": "l1_export_kw",
                "description": "Phase L1 active export power",
                "unit": "kW",
                "category": "phase_power",
            },
            "1_0:31_4_0": {
                "label": "l1_current_a_max",
                "description": "Phase L1 current limit / max",
                "unit": "A",
                "category": "phase_current",
            },
            "1_0:31_7_0": {
                "label": "l1_current_a",
                "description": "Phase L1 current",
                "unit": "A",
                "category": "phase_current",
            },
            "1_0:32_7_0": {
                "label": "l1_voltage_v",
                "description": "Phase L1 voltage",
                "unit": "V",
                "category": "phase_voltage",
            },
            "1_0:41_7_0": {
                "label": "l2_import_kw",
                "description": "Phase L2 active import power",
                "unit": "kW",
                "category": "phase_power",
            },
            "1_0:42_7_0": {
                "label": "l2_export_kw",
                "description": "Phase L2 active export power",
                "unit": "kW",
                "category": "phase_power",
            },
            "1_0:51_7_0": {
                "label": "l2_current_a",
                "description": "Phase L2 current",
                "unit": "A",
                "category": "phase_current",
            },
            "1_0:52_7_0": {
                "label": "l2_voltage_v",
                "description": "Phase L2 voltage",
                "unit": "V",
                "category": "phase_voltage",
            },
            "1_0:61_7_0": {
                "label": "l3_import_kw",
                "description": "Phase L3 active import power",
                "unit": "kW",
                "category": "phase_power",
            },
            "1_0:62_7_0": {
                "label": "l3_export_kw",
                "description": "Phase L3 active export power",
                "unit": "kW",
                "category": "phase_power",
            },
            "1_0:71_7_0": {
                "label": "l3_current_a",
                "description": "Phase L3 current",
                "unit": "A",
                "category": "phase_current",
            },
            "1_0:72_7_0": {
                "label": "l3_voltage_v",
                "description": "Phase L3 voltage",
                "unit": "V",
                "category": "phase_voltage",
            },
        }

    def _to_iso(self, value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return None
        return str(value)

    def _try_float(self, value: Any):
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _normalize_field_name(self, field: str) -> str:
        return field.replace(".", "_").replace("-", "_").replace("/", "_")

    def query_latest_all_fields(self, range_window: str = "-30d") -> dict[str, dict[str, Any]]:
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {range_window})
  |> filter(fn: (r) => r._measurement == "{self.measurement}")
  |> last()
'''
        tables = self.query_api.query(flux)
        result: dict[str, dict[str, Any]] = {}

        for table in tables:
            for record in table.records:
                field = record.get_field()
                raw_value = record.get_value()

                result[field] = {
                    "field": field,
                    "normalized_field": self._normalize_field_name(field),
                    "value": raw_value,
                    "value_num": self._try_float(raw_value),
                    "time": self._to_iso(record.get_time()),
                    "measurement": record.get_measurement(),
                }

        return result

    def decode_all_fields(self, range_window: str = "-30d") -> dict[str, Any]:
        all_fields = self.query_latest_all_fields(range_window=range_window)

        decoded = []
        timestamps = []

        for field_name in sorted(all_fields.keys()):
            rec = all_fields[field_name]
            meta = self.known_obis.get(field_name)

            if rec.get("time"):
                timestamps.append(rec["time"])

            decoded.append({
                "field": field_name,
                "normalized_field": rec["normalized_field"],
                "label": meta["label"] if meta else rec["normalized_field"],
                "description": meta["description"] if meta else "Unknown / unmapped OBIS field",
                "category": meta["category"] if meta else "unknown",
                "unit": meta["unit"] if meta else None,
                "value": rec["value"],
                "value_num": rec["value_num"],
                "time": rec["time"],
            })

        return {
            "status": "ok" if decoded else "no_data",
            "source": {
                "bucket": self.bucket,
                "measurement": self.measurement,
            },
            "timestamp": max(timestamps) if timestamps else None,
            "count": len(decoded),
            "fields": decoded,
        }

    def get_energy_summary(self) -> dict[str, Any]:
        all_fields = self.query_latest_all_fields()

        def get_num(field: str):
            rec = all_fields.get(field)
            return rec["value_num"] if rec else None

        def get_raw(field: str):
            rec = all_fields.get(field)
            return rec["value"] if rec else None

        import_t1 = get_num("1_0:1_8_1")
        import_t2 = get_num("1_0:1_8_2")
        export_t1 = get_num("1_0:2_8_1")
        export_t2 = get_num("1_0:2_8_2")
        current_import_kw = get_num("1_0:1_7_0")
        current_export_kw = get_num("1_0:2_7_0")
        current_avg_demand_kw = get_num("1_0:1_4_0")

        total_import_kwh = None
        if import_t1 is not None or import_t2 is not None:
            total_import_kwh = (import_t1 or 0.0) + (import_t2 or 0.0)

        total_export_kwh = None
        if export_t1 is not None or export_t2 is not None:
            total_export_kwh = (export_t1 or 0.0) + (export_t2 or 0.0)

        provider_net_power_kw = None
        if current_import_kw is not None or current_export_kw is not None:
            provider_net_power_kw = (current_import_kw or 0.0) - (current_export_kw or 0.0)

        timestamps = [rec["time"] for rec in all_fields.values() if rec.get("time")]

        return {
            "status": "ok" if all_fields else "no_data",
            "source": {
                "bucket": self.bucket,
                "measurement": self.measurement,
            },
            "timestamp": max(timestamps) if timestamps else None,
            "meter_id": str(get_raw("0_0:96_1_1")) if get_raw("0_0:96_1_1") is not None else None,
            "tariff_indicator": get_raw("0_0:96_14_0"),
            "import_t1_kwh": import_t1,
            "import_t2_kwh": import_t2,
            "export_t1_kwh": export_t1,
            "export_t2_kwh": export_t2,
            "total_import_kwh": total_import_kwh,
            "total_export_kwh": total_export_kwh,
            "current_import_kw": current_import_kw,
            "current_export_kw": current_export_kw,
            "current_average_demand_kw": current_avg_demand_kw,
            "provider_net_power_kw": provider_net_power_kw,
            "l1_import_kw": get_num("1_0:21_7_0"),
            "l1_export_kw": get_num("1_0:22_7_0"),
            "l2_import_kw": get_num("1_0:41_7_0"),
            "l2_export_kw": get_num("1_0:42_7_0"),
            "l3_import_kw": get_num("1_0:61_7_0"),
            "l3_export_kw": get_num("1_0:62_7_0"),
            "l1_current_a": get_num("1_0:31_7_0"),
            "l2_current_a": get_num("1_0:51_7_0"),
            "l3_current_a": get_num("1_0:71_7_0"),
            "l1_voltage_v": get_num("1_0:32_7_0"),
            "l2_voltage_v": get_num("1_0:52_7_0"),
            "l3_voltage_v": get_num("1_0:72_7_0"),
            "raw_fields_available": sorted(all_fields.keys()),
            "resolved_fields": {
                "meter_id": "0_0:96_1_1" if "0_0:96_1_1" in all_fields else None,
                "tariff_indicator": "0_0:96_14_0" if "0_0:96_14_0" in all_fields else None,
                "import_t1_kwh": "1_0:1_8_1" if "1_0:1_8_1" in all_fields else None,
                "import_t2_kwh": "1_0:1_8_2" if "1_0:1_8_2" in all_fields else None,
                "export_t1_kwh": "1_0:2_8_1" if "1_0:2_8_1" in all_fields else None,
                "export_t2_kwh": "1_0:2_8_2" if "1_0:2_8_2" in all_fields else None,
                "current_import_kw": "1_0:1_7_0" if "1_0:1_7_0" in all_fields else None,
                "current_export_kw": "1_0:2_7_0" if "1_0:2_7_0" in all_fields else None,
                "current_average_demand_kw": "1_0:1_4_0" if "1_0:1_4_0" in all_fields else None,
            },
        }

    def get_gas_summary(self) -> dict[str, Any]:
        all_fields = self.query_latest_all_fields()

        def get_num(field: str):
            rec = all_fields.get(field)
            return rec["value_num"] if rec else None

        def get_raw(field: str):
            rec = all_fields.get(field)
            return rec["value"] if rec else None

        gas_total_m3 = None
        gas_source_field = None

        for candidate in ["0_1:24_2_1", "0_1:24_2_3", "0_1:24_3_0"]:
            value = get_num(candidate)
            if value is not None:
                gas_total_m3 = value
                gas_source_field = candidate
                break

        gas_fields = []
        for field_name, rec in all_fields.items():
            if field_name.startswith("0_1:24_"):
                meta = self.known_obis.get(field_name)
                gas_fields.append({
                    "field": field_name,
                    "label": meta["label"] if meta else rec["normalized_field"],
                    "description": meta["description"] if meta else "Gas-related field",
                    "value": rec["value"],
                    "value_num": rec["value_num"],
                    "time": rec["time"],
                })

        timestamps = [rec["time"] for rec in all_fields.values() if rec.get("time")]

        status_text = "unknown"
        valve_status = get_raw("0_1:24_4_0")
        if valve_status is not None:
            if str(valve_status) in {"1", "1.0"}:
                status_text = "available"
            elif str(valve_status) in {"0", "0.0"}:
                status_text = "inactive"
            else:
                status_text = f"state_{valve_status}"

        return {
            "status": "ok" if gas_fields else "no_data",
            "timestamp": max(timestamps) if timestamps else None,
            "gas_meter_id": str(get_raw("0_1:24_1_0")) if get_raw("0_1:24_1_0") is not None else None,
            "gas_valve_status": valve_status,
            "gas_status_text": status_text,
            "gas_total_m3": gas_total_m3,
            "gas_total_source_field": gas_source_field,
            "gas_fields": sorted(gas_fields, key=lambda x: x["field"]),
        }

    def compare_with_local_meter(self, local_energy_summary: dict[str, Any]) -> dict[str, Any]:
        pdata = self.get_energy_summary()

        local_import = local_energy_summary.get("import_kwh_total")
        local_export = local_energy_summary.get("export_kwh_total")
        local_power_w = local_energy_summary.get("power_watts")

        provider_import = pdata.get("total_import_kwh")
        provider_export = pdata.get("total_export_kwh")
        provider_net_power_kw = pdata.get("provider_net_power_kw")

        import_delta_kwh = None
        if provider_import is not None and local_import is not None:
            import_delta_kwh = provider_import - local_import

        export_delta_kwh = None
        if provider_export is not None and local_export is not None:
            export_delta_kwh = provider_export - local_export

        power_delta_w = None
        provider_net_power_w = None
        if provider_net_power_kw is not None:
            provider_net_power_w = provider_net_power_kw * 1000.0
        if provider_net_power_w is not None and local_power_w is not None:
            power_delta_w = provider_net_power_w - local_power_w

        return {
            "status": "ok" if pdata.get("status") == "ok" else "no_data",
            "timestamp": pdata.get("timestamp"),
            "local_meter": {
                "source": "house meter",
                "import_kwh_total": local_import,
                "export_kwh_total": local_export,
                "power_watts": local_power_w,
            },
            "provider_meter": {
                "source": "Pdata / utility meter",
                "meter_id": pdata.get("meter_id"),
                "tariff_indicator": pdata.get("tariff_indicator"),
                "import_t1_kwh": pdata.get("import_t1_kwh"),
                "import_t2_kwh": pdata.get("import_t2_kwh"),
                "export_t1_kwh": pdata.get("export_t1_kwh"),
                "export_t2_kwh": pdata.get("export_t2_kwh"),
                "total_import_kwh": pdata.get("total_import_kwh"),
                "total_export_kwh": pdata.get("total_export_kwh"),
                "current_import_kw": pdata.get("current_import_kw"),
                "current_export_kw": pdata.get("current_export_kw"),
                "provider_net_power_kw": pdata.get("provider_net_power_kw"),
                "resolved_fields": pdata.get("resolved_fields"),
            },
            "deltas": {
                "import_kwh": import_delta_kwh,
                "export_kwh": export_delta_kwh,
                "net_power_w": power_delta_w,
            },
            "raw_fields_available": pdata.get("raw_fields_available", []),
        }

    def get_full_overview(self) -> dict[str, Any]:
        summary = self.get_energy_summary()
        decoded = self.decode_all_fields()
        gas = self.get_gas_summary()

        return {
            "status": "ok" if summary.get("status") == "ok" else "no_data",
            "timestamp": summary.get("timestamp"),
            "summary": summary,
            "gas": gas,
            "all_fields": decoded,
        }
