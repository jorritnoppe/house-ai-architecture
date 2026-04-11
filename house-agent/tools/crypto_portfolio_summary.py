from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_portfolio_summary",
    "description": "Get the current crypto portfolio total value, coin count, largest holding, and symbol breakdown.",
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

    result = crypto_tools.get_current_portfolio_summary()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto portfolio value is {result.get('total_value', 'unknown')}, "
            f"across {result.get('coin_count', 'unknown')} coins."
        ),
    }
