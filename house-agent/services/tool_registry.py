import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    safety: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    module_name: str


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def list_tool_specs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "safety": tool.safety,
                "module_name": tool.module_name,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.handler(args or {})


def load_tools_from_package(package_name: str = "tools") -> ToolRegistry:
    registry = ToolRegistry()

    package = importlib.import_module(package_name)

    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue

        module_name = f"{package_name}.{module_info.name}"
        module = importlib.import_module(module_name)

        tool_spec = getattr(module, "TOOL_SPEC", None)
        tool_run = getattr(module, "run", None)

        if tool_spec is None or tool_run is None:
            continue

        required_keys = ["name", "description", "parameters", "safety"]
        missing = [key for key in required_keys if key not in tool_spec]
        if missing:
            raise ValueError(f"{module_name} missing TOOL_SPEC keys: {missing}")

        registry.register(
            Tool(
                name=tool_spec["name"],
                description=tool_spec["description"],
                parameters=tool_spec["parameters"],
                safety=tool_spec["safety"],
                handler=tool_run,
                module_name=module_name,
            )
        )

    return registry
