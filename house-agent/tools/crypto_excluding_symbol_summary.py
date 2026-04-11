from typing import Any

TOOL_SPEC = {
    "name": "get_crypto_excluding_symbol_summary",
    "description": "Get portfolio summary excluding one specific crypto symbol.",
    "parameters": {
        "type": "object",
        "properties": {
            "exclude_symbol": {
                "type": "string",
                "description": "Crypto symbol to exclude, such as XRP.",
                "default": "XRP",
            }
        },
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from extensions import crypto_tools

    exclude_symbol = str(args.get("exclude_symbol", "XRP")).upper().strip()
    result = crypto_tools.get_excluding_symbol_summary(exclude_symbol)

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": (
            f"Crypto summary excluding {exclude_symbol}: total value is "
            f"{result.get('total_value_excluding_symbol', 'unknown')}."
        ),
    }
