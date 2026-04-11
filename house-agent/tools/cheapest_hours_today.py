from typing import Any

TOOL_SPEC = {
    "name": "get_cheapest_hours_today",
    "description": "Get the cheapest electricity price windows seen today.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.price_service import get_cheapest_hours_today

    limit = args.get("limit", 3)
    result = get_cheapest_hours_today(limit=limit)

    items = result.get("items", [])
    if items:
        top = ", ".join(
            f"{item.get('time')} at {item.get('price_eur_per_kwh')} EUR/kWh"
            for item in items
        )
        answer = f"Cheapest price windows today: {top}."
    else:
        answer = "No cheapest-hours data found for today."

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": answer,
    }
