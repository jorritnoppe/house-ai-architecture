from typing import Any

TOOL_SPEC = {
    "name": "get_pdata_full_overview",
    "description": "Get the full Pdata overview including all important values.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.pdata_service import get_pdata_full_overview_data

    result = get_pdata_full_overview_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "The full Pdata overview has been retrieved.",
    }
