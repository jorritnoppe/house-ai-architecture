from typing import Any

TOOL_SPEC = {
    "name": "get_pdata_compare_energy",
    "description": "Compare the Pdata meter values with the local energy meter summary.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    from services.pdata_service import get_pdata_compare_energy_data

    result = get_pdata_compare_energy_data()

    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": result,
        "answer": "Pdata comparison with the local meter has been retrieved.",
    }
