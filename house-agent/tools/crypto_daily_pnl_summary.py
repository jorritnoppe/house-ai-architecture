from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_daily_pnl_summary",
    "description": "Get the crypto portfolio 24-hour profit and loss summary with best and worst contributors.",
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

    result = crypto_tools.get_daily_pnl_summary()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto portfolio 24h PnL is {result.get('delta', 'unknown')} "
            f"({result.get('delta_pct', 'unknown')}%)."
        ),
    }
