"""
Tool Registry Implementation.
"""

from core.tools.interfaces import ITool, IToolRegistry
from core.tools.models import ToolSchema


class ToolRegistry(IToolRegistry):
    """
    Registry for managing Tools by their Fully Qualified Name (FQN).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ITool] = {}

    def register(self, tool: ITool) -> None:
        """Register a new tool. Throws an error on conflict."""
        fqn = tool.schema.fqn
        if fqn in self._tools:
            raise ValueError(f"Tool conflict: '{fqn}' is already registered.")
            
        self._tools[fqn] = tool

    def get_tool(self, fqn: str) -> ITool | None:
        return self._tools.get(fqn)

    def get_all_schemas(self) -> list[ToolSchema]:
        return [tool.schema for tool in self._tools.values()]
