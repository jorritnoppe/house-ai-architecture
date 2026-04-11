from typing import Any

TOOL_SPEC = {
    "name": "get_buderus_boiler_health_summary",
    "description": "Get an overall Buderus boiler health summary with score, status, and notes.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.buderus_service import get_buderus_boiler_health_summary_data

    result = get_buderus_boiler_health_summary_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No Buderus boiler health summary available."),
    }
