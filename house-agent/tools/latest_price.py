from typing import Any

TOOL_SPEC = {
    "name": "get_latest_price",
    "description": "Get the latest known electricity price in EUR per kWh.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.price_service import query_latest_price

    latest = query_latest_price()

    if not latest or latest.get("value") is None:
        result = {
            "status": "no_data",
            "message": "No electricity price data found.",
        }
    else:
        result = {
            "status": "ok",
            "timestamp": latest.get("time"),
            "price_eur_per_kwh": latest.get("value"),
            "source": {
                "measurement": latest.get("measurement"),
                "field": latest.get("field"),
            },
        }

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Latest electricity price is {result.get('price_eur_per_kwh', 'unknown')} EUR per kWh."
        ),
    }
