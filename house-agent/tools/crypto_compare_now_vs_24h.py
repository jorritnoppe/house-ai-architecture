from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_compare_now_vs_24h",
    "description": "Compare the crypto portfolio value now versus 24 hours ago.",
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

    result = crypto_tools.compare_portfolio_now_vs_24h()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto portfolio value is {result.get('current_total_value', 'unknown')} now "
            f"versus {result.get('value_24h_ago', 'unknown')} 24 hours ago."
        ),
    }
