from typing import Any

TOOL_SPEC = {
    "name": "get_water_temperature_summary",
    "description": "Get inlet water temperature, salt tank water temperature, and their difference.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.water_service import get_water_temperature_summary

    result = get_water_temperature_summary()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Inlet water temperature is {result.get('inlet_water_temp_c', 'unknown')} C, "
            f"salt tank water temperature is {result.get('salt_tank_water_temp_c', 'unknown')} C, "
            f"and temperature delta is {result.get('temp_delta_c', 'unknown')} C."
        ),
    }
