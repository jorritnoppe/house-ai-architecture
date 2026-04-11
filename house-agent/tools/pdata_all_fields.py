from typing import Any

TOOL_SPEC = {
    "name": "get_pdata_all_fields",
    "description": "Get all decoded Pdata fields.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.pdata_service import get_pdata_all_fields_data

    result = get_pdata_all_fields_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "All decoded Pdata fields have been retrieved.",
    }
