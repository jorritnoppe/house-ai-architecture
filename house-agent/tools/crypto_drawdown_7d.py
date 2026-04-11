from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_drawdown_7d",
    "description": "Get the 7-day drawdown analysis for the crypto portfolio symbols.",
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

    result = crypto_tools.get_drawdown_7d()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "Crypto 7-day drawdown analysis has been retrieved.",
    }
