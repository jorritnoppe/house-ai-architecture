from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_stale_data_check",
    "description": "Check whether any crypto portfolio symbols have stale data.",
    "parameters": {
        "type": "object",
        "properties": {
            "stale_hours": {
                "type": "integer",
                "description": "Threshold in hours above which data is considered stale.",
                "default": 12,
            }
        },
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from extensions import crypto_tools

    stale_hours = int(args.get("stale_hours", 12))
    result = crypto_tools.get_stale_data_check(stale_hours=stale_hours)

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto stale data check: {result.get('stale_count', 'unknown')} stale symbols, "
            f"threshold {stale_hours} hours."
        ),
    }
