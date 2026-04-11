from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_concentration_risk",
    "description": "Get crypto portfolio concentration risk, largest holding, top allocations, and HHI score.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from extensions import crypto_tools

    result = crypto_tools.get_concentration_risk()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto concentration risk is {result.get('risk_level', 'unknown')}. "
            f"Largest holding is {result.get('largest_holding', {}).get('symbol', 'unknown')}."
        ),
    }
