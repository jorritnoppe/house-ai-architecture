# ~/house-agent/services/energy_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from extensions import pdata_tools, sma_tools


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class EnergySnapshot:
    status: str
    timestamp: str
    pdata: dict[str, Any]
    sma: dict[str, Any]
    derived: dict[str, Any]


class EnergyService:
    """Unified house energy service.

    Combines utility meter data (Pdata) with solar inverter data (SMA)
    into one normalized energy view for routes, dashboards, and AI logic.
    """

    def get_live_snapshot(self) -> dict[str, Any]:
        pdata = pdata_tools.get_energy_summary()
        sma = sma_tools.get_summary()

        pdata_status = pdata.get("status", "unknown")
        sma_status = sma.get("status", "unknown")

        solar_power_kw = _safe_float(sma.get("ac_power_kw"))
        grid_import_kw = _safe_float(pdata.get("current_import_kw"))
        grid_export_kw = _safe_float(pdata.get("current_export_kw"))

        net_grid_kw = grid_import_kw - grid_export_kw
        estimated_house_load_kw = solar_power_kw + grid_import_kw - grid_export_kw
        self_consumed_solar_kw = max(0.0, solar_power_kw - grid_export_kw)
        power_balance_kw = estimated_house_load_kw - (solar_power_kw + net_grid_kw)

        overall_status = "ok"
        if pdata_status != "ok" and sma_status != "ok":
            overall_status = "degraded"
        elif pdata_status != "ok" or sma_status != "ok":
            overall_status = "partial"

        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "status": overall_status,
            "timestamp": timestamp,
            "pdata": pdata,
            "sma": sma,
            "derived": {
                "solar_power_kw": round(solar_power_kw, 3),
                "grid_import_kw": round(grid_import_kw, 3),
                "grid_export_kw": round(grid_export_kw, 3),
                "net_grid_kw": round(net_grid_kw, 3),
                "estimated_house_load_kw": round(estimated_house_load_kw, 3),
                "self_consumed_solar_kw": round(self_consumed_solar_kw, 3),
                "power_balance_kw": round(power_balance_kw, 6),
                "source_status": {
                    "pdata": pdata_status,
                    "sma": sma_status,
                },
            },
        }

    def get_power_flow_summary(self) -> dict[str, Any]:
        snapshot = self.get_live_snapshot()
        derived = snapshot["derived"]

        return {
            "status": snapshot["status"],
            "timestamp": snapshot["timestamp"],
            "solar_power_kw": derived["solar_power_kw"],
            "grid_import_kw": derived["grid_import_kw"],
            "grid_export_kw": derived["grid_export_kw"],
            "net_grid_kw": derived["net_grid_kw"],
            "estimated_house_load_kw": derived["estimated_house_load_kw"],
            "self_consumed_solar_kw": derived["self_consumed_solar_kw"],
            "source_status": derived["source_status"],
        }

    def get_energy_ai_summary(self) -> dict[str, Any]:
        summary = self.get_power_flow_summary()

        solar = summary["solar_power_kw"]
        grid_in = summary["grid_import_kw"]
        grid_out = summary["grid_export_kw"]
        load = summary["estimated_house_load_kw"]

        if grid_in > 0 and solar > 0:
            answer = (
                f"Right now the house is using about {load:.2f} kilowatts. "
                f"Solar is producing {solar:.2f} kilowatts and the house is still importing "
                f"{grid_in:.2f} kilowatts from the grid."
            )
        elif grid_out > 0 and solar > 0:
            answer = (
                f"Right now solar is producing {solar:.2f} kilowatts. "
                f"The house load is about {load:.2f} kilowatts and about "
                f"{grid_out:.2f} kilowatts is being exported to the grid."
            )
        elif solar <= 0 and grid_in > 0:
            answer = (
                f"Right now solar production is {solar:.2f} kilowatts. "
                f"The house is importing about {grid_in:.2f} kilowatts from the grid, "
                f"with an estimated load of {load:.2f} kilowatts."
            )
        else:
            answer = (
                f"Right now estimated house load is {load:.2f} kilowatts, "
                f"solar production is {solar:.2f} kilowatts, and net grid flow is "
                f"{summary['net_grid_kw']:.2f} kilowatts."
            )

        return {
            "status": summary["status"],
            "timestamp": summary["timestamp"],
            "answer": answer,
            "structured": summary,
        }


energy_service = EnergyService()
