from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_contributors_24h",
    "description": "Get the best and worst crypto contributors over the last 24 hours.",
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

    result = crypto_tools.get_contributors_24h()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "Crypto contributors over the last 24 hours have been retrieved.",
    }
