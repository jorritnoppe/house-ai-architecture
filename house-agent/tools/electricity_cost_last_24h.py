from typing import Any

TOOL_SPEC = {
    "name": "get_electricity_cost_last_24h",
    "description": "Calculate total imported electricity cost over the last 24 hours.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.price_service import get_electricity_cost_last_24h

    result = get_electricity_cost_last_24h()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Electricity import cost over the last 24 hours is {result.get('total_cost_eur', 'unknown')} EUR "
            f"for {result.get('total_import_kwh', 'unknown')} kWh imported."
        ),
    }
