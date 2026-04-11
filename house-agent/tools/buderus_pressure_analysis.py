from typing import Any

TOOL_SPEC = {
    "name": "get_buderus_pressure_analysis",
    "description": "Analyze Buderus boiler system pressure and return a recommendation.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.buderus_service import get_buderus_pressure_analysis_data

    result = get_buderus_pressure_analysis_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No Buderus pressure analysis available."),
    }
