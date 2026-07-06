from typing import Dict, Type
from app.ai.tools.base import BaseTool

class ToolRegistry:
    """
    Registry for all available AI tools.
    Agents can request tools by name from the registry.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} is already registered.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool {name} not found in registry.")
        return tool

    def get_all_tools(self) -> Dict[str, BaseTool]:
        return self._tools.copy()

# Singleton instance
tool_registry = ToolRegistry()
