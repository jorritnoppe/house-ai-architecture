from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_compare_7d",
    "description": "Compare the crypto portfolio value now versus 7 days ago.",
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

    result = crypto_tools.get_compare_7d()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto portfolio value is {result.get('current_total_value', 'unknown')} now "
            f"versus {result.get('value_7d_ago', 'unknown')} 7 days ago."
        ),
    }
