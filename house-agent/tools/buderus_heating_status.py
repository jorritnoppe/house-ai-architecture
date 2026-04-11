from typing import Any

TOOL_SPEC = {
    "name": "get_buderus_heating_status",
    "description": "Get Buderus space-heating status including heating activity, burner state, temperatures, and pressure.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.buderus_service import get_buderus_heating_status_data

    result = get_buderus_heating_status_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No Buderus heating status available."),
    }
