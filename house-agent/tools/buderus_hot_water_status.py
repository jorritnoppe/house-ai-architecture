from typing import Any

TOOL_SPEC = {
    "name": "get_buderus_hot_water_status",
    "description": "Get Buderus hot water status including DHW current and target temperatures.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.buderus_service import get_buderus_hot_water_status_data

    result = get_buderus_hot_water_status_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No Buderus hot water status available."),
    }
