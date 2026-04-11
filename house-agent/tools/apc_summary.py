from typing import Any

TOOL_SPEC = {
    "name": "get_apc_summary",
    "description": "Get a general summary of all APC UPS devices including power source, load, battery, runtime, and voltage state.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.apc_service import get_apc_summary_data

    result = get_apc_summary_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No APC UPS summary available."),
    }
