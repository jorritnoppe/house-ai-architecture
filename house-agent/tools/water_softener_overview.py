from typing import Any

TOOL_SPEC = {
    "name": "get_water_softener_overview",
    "description": "Get a combined overview of water softener salt level, water temperatures, and refill warning.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.water_service import get_water_softener_overview

    result = get_water_softener_overview()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Water softener overview: refill warning is {result.get('refill_warning', 'unknown')}, "
            f"salt status is {result.get('salt', {}).get('salt_level_status', 'unknown')}, "
            f"and inlet water temperature is {result.get('temperatures', {}).get('inlet_water_temp_c', 'unknown')} C."
        ),
    }
