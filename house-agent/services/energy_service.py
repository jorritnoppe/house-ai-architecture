from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from extensions import pdata_tools, sma_tools


EXPORT_RESERVE_KW = 0.5
EXCESS_LOW_THRESHOLD_KW = 0.5
EXCESS_MEDIUM_THRESHOLD_KW = 1.5
EXCESS_HIGH_THRESHOLD_KW = 3.0


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

    def _classify_excess_energy_state(self, excess_energy_available_kw: float) -> str:
        if excess_energy_available_kw >= EXCESS_HIGH_THRESHOLD_KW:
            return "high"
        if excess_energy_available_kw >= EXCESS_MEDIUM_THRESHOLD_KW:
            return "medium"
        if excess_energy_available_kw >= EXCESS_LOW_THRESHOLD_KW:
            return "low"
        return "none"

    def get_live_snapshot(self) -> dict[str, Any]:
        pdata = pdata_tools.get_energy_summary()
        sma = sma_tools.get_summary()

        pdata_status = pdata.get("status", "unknown")
        sma_status = sma.get("status", "unknown")

        solar_power_kw = _safe_float(sma.get("ac_power_kw"))
        grid_import_kw = _safe_float(pdata.get("current_import_kw"))
        grid_export_kw = _safe_float(pdata.get("current_export_kw"))

        net_grid_kw = grid_import_kw - grid_export_kw

        # House-level estimate:
        # house load = solar production + imported grid - exported grid
        estimated_house_load_kw = max(0.0, solar_power_kw + grid_import_kw - grid_export_kw)

        # Of the solar currently produced, how much is staying in the house
        self_consumed_solar_kw = max(0.0, solar_power_kw - grid_export_kw)

        # Automation-safe "free electricity" signal
        excess_energy_available_kw = max(0.0, grid_export_kw - EXPORT_RESERVE_KW)
        excess_energy_state = self._classify_excess_energy_state(excess_energy_available_kw)

        if grid_export_kw > 0:
            excess_energy_reason = "exporting_to_grid"
        elif grid_import_kw > 0:
            excess_energy_reason = "importing_from_grid"
        elif solar_power_kw > 0:
            excess_energy_reason = "solar_covering_load"
        else:
            excess_energy_reason = "no_meaningful_excess"

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
                "excess_energy_available_kw": round(excess_energy_available_kw, 3),
                "excess_energy_state": excess_energy_state,
                "excess_energy_reason": excess_energy_reason,
                "export_reserve_kw": round(EXPORT_RESERVE_KW, 3),
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
            "excess_energy_available_kw": derived["excess_energy_available_kw"],
            "excess_energy_state": derived["excess_energy_state"],
            "excess_energy_reason": derived["excess_energy_reason"],
            "export_reserve_kw": derived["export_reserve_kw"],
            "source_status": derived["source_status"],
        }

    def get_energy_ai_summary(self) -> dict[str, Any]:
        summary = self.get_power_flow_summary()

        solar = summary["solar_power_kw"]
        grid_in = summary["grid_import_kw"]
        grid_out = summary["grid_export_kw"]
        load = summary["estimated_house_load_kw"]
        excess = summary["excess_energy_available_kw"]
        excess_state = summary["excess_energy_state"]

        if excess > 0:
            answer = (
                f"The house is currently using about {load:.2f} kilowatts. "
                f"Solar is producing {solar:.2f} kilowatts and exporting {grid_out:.2f} kilowatts. "
                f"There is about {excess:.2f} kilowatts of excess electricity available "
                f"after keeping a {summary['export_reserve_kw']:.2f} kilowatt reserve. "
                f"Excess energy state is {excess_state}."
            )
        elif grid_in > 0 and solar > 0:
            answer = (
                f"The house is currently using about {load:.2f} kilowatts. "
                f"Solar is producing {solar:.2f} kilowatts, but the house still imports "
                f"{grid_in:.2f} kilowatts from the grid."
            )
        elif solar <= 0 and grid_in > 0:
            answer = (
                f"Solar production is {solar:.2f} kilowatts right now. "
                f"The house is importing about {grid_in:.2f} kilowatts from the grid, "
                f"with an estimated load of {load:.2f} kilowatts."
            )
        else:
            answer = (
                f"The house is currently using about {load:.2f} kilowatts. "
                f"Solar production is {solar:.2f} kilowatts. "
                f"There is no automation-safe excess electricity available right now."
            )

        return {
            "status": summary["status"],
            "timestamp": summary["timestamp"],
            "answer": answer,
            "structured": summary,
        }


energy_service = EnergyService()
