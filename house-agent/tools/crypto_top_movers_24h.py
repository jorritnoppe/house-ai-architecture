from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_top_movers_24h",
    "description": "Get the top crypto movers over the last 24 hours by value change.",
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

    result = crypto_tools.get_top_movers_24h()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "Top crypto movers over the last 24 hours have been retrieved.",
    }
