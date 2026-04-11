from typing import Any

TOOL_SPEC = {
    "name": "get_salt_tank_level",
    "description": "Get the current water softener salt tank level, percentage, and refill status.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.water_service import get_salt_tank_level

    result = get_salt_tank_level()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Salt tank level is {result.get('salt_level_percent', 'unknown')}%, "
            f"distance is {result.get('distance_cm', 'unknown')} cm, "
            f"status is {result.get('salt_level_status', 'unknown')}."
        ),
    }
