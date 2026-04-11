from typing import Any


TOOL_SPEC = {
    "name": "experimental_test_ping",
    "description": "Simple experimental test tool that echoes a message.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to echo back."
            }
        },
        "required": [],
        "additionalProperties": False,
    },
    "safety": "read_only",
    "stage": "experimental",
    "approval_required": True,
}


def run(args: dict[str, Any]) -> dict[str, Any]:
    message = args.get("message", "hello from experimental tool")
    return {
        "ok": True,
        "tool_name": TOOL_SPEC["name"],
        "data": {
            "message": message,
            "stage": "experimental",
        },
        "answer": f"Experimental tool responded with message: {message}",
    }
