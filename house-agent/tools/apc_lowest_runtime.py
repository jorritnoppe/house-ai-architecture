from typing import Any

TOOL_SPEC = {
    "name": "get_apc_lowest_runtime",
    "description": "Find the APC UPS with the shortest remaining runtime.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.apc_service import get_apc_lowest_runtime_data

    result = get_apc_lowest_runtime_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No APC runtime summary available."),
    }
