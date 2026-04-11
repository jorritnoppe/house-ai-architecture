from typing import Any

TOOL_SPEC = {
    "name": "get_pdata_energy_summary",
    "description": "Get the main household power and energy summary from the Pdata meter.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.pdata_service import get_pdata_energy_summary_data

    result = get_pdata_energy_summary_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Current household energy summary: "
            f"power is {result.get('power_watts', 'unknown')} W, "
            f"import total is {result.get('import_kwh_total', 'unknown')} kWh, "
            f"export total is {result.get('export_kwh_total', 'unknown')} kWh, "
            f"frequency is {result.get('frequency_hz', 'unknown')} Hz, "
            f"power factor is {result.get('power_factor', 'unknown')}."
        ),
    }
