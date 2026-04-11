from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_coin_summary",
    "description": "Get summary for a single crypto symbol including amount, price, and value.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Crypto symbol such as XRP, BTC, or ETH.",
            }
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from extensions import crypto_tools

    symbol = str(args.get("symbol", "")).upper().strip()
    result = crypto_tools.get_coin_summary(symbol)

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"{symbol} summary: amount is {result.get('amount', 'unknown')}, "
            f"price is {result.get('price', 'unknown')}, "
            f"value is {result.get('value', 'unknown')}."
        ),
    }
