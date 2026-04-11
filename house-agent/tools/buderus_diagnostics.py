from typing import Any

TOOL_SPEC = {
    "name": "get_buderus_diagnostics",
    "description": "Get Buderus diagnostics including error code, service code, and maintenance message.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.buderus_service import get_buderus_diagnostics_data

    result = get_buderus_diagnostics_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": result.get("answer", "No Buderus diagnostics available."),
    }
