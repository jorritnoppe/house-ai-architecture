from typing import Any

TOOL_SPEC = {
    "name": "get_pdata_gas_summary",
    "description": "Get the gas usage summary from the Pdata meter.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.pdata_service import get_pdata_gas_summary_data

    result = get_pdata_gas_summary_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "The gas summary has been retrieved.",
    }
