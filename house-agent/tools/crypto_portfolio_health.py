from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_portfolio_health",
    "description": "Get crypto portfolio health including value, 24h delta, concentration risk, stale data, and contributors.",
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

    result = crypto_tools.get_portfolio_health()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto portfolio health: total value {result.get('total_value', 'unknown')}, "
            f"24h delta {result.get('delta_24h', 'unknown')}, "
            f"risk level {result.get('risk_level', 'unknown')}."
        ),
    }
