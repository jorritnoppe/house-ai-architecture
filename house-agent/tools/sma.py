from typing import Any

TOOL_SPEC = {
    "name": "get_sma_overview",
    "description": "Get current SMA inverter production overview.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from extensions import sma_tools

    result = sma_tools.get_production_overview()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            "SMA production overview: "
            f"AC output is {result['ac_power_w']} W, "
            f"today's solar energy is {result['daily_energy_kwh']} kWh, "
            f"total lifetime production is {result['total_energy_kwh']} kWh, "
            f"PV voltage is {result['pv_voltage_v']} V, "
            f"PV current is {result['pv_current_a']} A, "
            f"grid voltage is {result['grid_voltage_v']} V, "
            f"and inverter temperature is {result['inverter_temp_c']} C."
        ),
    }
