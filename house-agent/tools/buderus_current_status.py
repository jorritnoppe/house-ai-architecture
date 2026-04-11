from typing import Any

TOOL_SPEC = {
    "name": "get_buderus_current_status",
    "description": "Get the current Buderus boiler status including mode, burner state, temperatures, and pressure.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.buderus_service import get_buderus_current_status_data

    result = get_buderus_current_status_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No Buderus current status available."),
    }
