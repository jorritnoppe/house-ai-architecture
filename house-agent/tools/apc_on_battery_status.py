from typing import Any

TOOL_SPEC = {
    "name": "get_apc_on_battery_status",
    "description": "Check whether any APC UPS is currently running on battery.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.apc_service import get_apc_on_battery_status_data

    result = get_apc_on_battery_status_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No APC on-battery status available."),
    }
