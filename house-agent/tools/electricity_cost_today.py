from typing import Any

TOOL_SPEC = {
    "name": "get_electricity_cost_today",
    "description": "Calculate total imported electricity cost for today.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.price_service import get_electricity_cost_today

    result = get_electricity_cost_today()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Today's electricity import cost is {result.get('total_cost_eur', 'unknown')} EUR "
            f"for {result.get('total_import_kwh', 'unknown')} kWh imported."
        ),
    }
