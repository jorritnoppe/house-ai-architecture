import json
from pathlib import Path

from services.internal_route_executor import execute_internal_route

ROOT = Path("/home/jnoppe/house-agent/house-ai-knowledge/policy")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_route_paths(raw):
    """
    Supports:
    1. {"routes": ["/a", "/b"]}
    2. [{"path": "/a"}, {"path": "/b"}]
    3. ["/a", "/b"]
    """
    if isinstance(raw, dict):
        items = raw.get("routes", [])
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    result = set()
    for item in items:
        if isinstance(item, str):
            result.add(item)
        elif isinstance(item, dict) and "path" in item:
            result.add(item["path"])
    return result


def _normalize_tool_names(raw):
    """
    Supports:
    1. {"tools": ["name1", "name2"]}
    2. [{"tool_name": "name1"}, {"tool_name": "name2"}]
    3. ["name1", "name2"]
    """
    if isinstance(raw, dict):
        items = raw.get("tools", [])
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    result = set()
    for item in items:
        if isinstance(item, str):
            result.add(item)
        elif isinstance(item, dict) and "tool_name" in item:
            result.add(item["tool_name"])
    return result


SAFE_ROUTE_RAW = _read_json(ROOT / "safe_route_allowlist.json")
SAFE_TOOL_RAW = _read_json(ROOT / "safe_tool_allowlist.json")

SAFE_ROUTE_PATHS = _normalize_route_paths(SAFE_ROUTE_RAW)
SAFE_TOOL_NAMES = _normalize_tool_names(SAFE_TOOL_RAW)


def call_route(path, params=None):
    try:
        data = execute_internal_route(path, params or {})
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def call_tool(tool_name, args=None):
    try:
        from services.tool_registry import execute
        return {"status": "ok", "data": execute(tool_name, args or {})}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def execute_safe_action(action):
    """
    action = {
        "type": "route" | "tool",
        "target": "...",
        "params": {}
    }
    """
    action_type = action.get("type")
    target = action.get("target")
    params = action.get("params", {})

    if action_type == "route":
        if target not in SAFE_ROUTE_PATHS:
            return {
                "status": "blocked",
                "reason": f"Route not allowed: {target}"
            }
        return call_route(target, params)

    if action_type == "tool":
        if target not in SAFE_TOOL_NAMES:
            return {
                "status": "blocked",
                "reason": f"Tool not allowed: {target}"
            }
        return call_tool(target, params)

    return {"status": "error", "error": "Invalid action type"}
