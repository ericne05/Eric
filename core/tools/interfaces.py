"""
Tool System Interfaces.
"""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from core.tools.models import ToolResult, ToolSchema

if TYPE_CHECKING:
    from core.agents.interfaces import ExecutionContext


class ITool(ABC):
    """
    Represents an executable Tool.
    """
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """The schema and metadata of this tool."""
        pass

    @abstractmethod
    async def execute_async(self, context: "ExecutionContext", cancellation_token: "CancellationToken | None" = None, **kwargs) -> ToolResult:
        """
        Execute the tool asynchronously.
        If the underlying function is sync, the decorator/executor should wrap it.
        """
        pass


class IToolRegistry(ABC):
    """
    Registry for all Tools (managed by FQN).
    """
    @abstractmethod
    def register(self, tool: ITool) -> None:
        """Register a new tool."""
        pass

    @abstractmethod
    def get_tool(self, fqn: str) -> ITool | None:
        """Retrieve a tool by Fully Qualified Name."""
        pass

    @abstractmethod
    def get_all_schemas(self) -> list[ToolSchema]:
        """Return schemas of all registered tools."""
        pass


class IToolExecutor(ABC):
    """
    Facade for executing Tools safely.
    Handles permissions, timeout, retry, and event tracking.
    """
    @abstractmethod
    async def execute_tool(self, context: "ExecutionContext", fqn: str, cancellation_token: "CancellationToken | None" = None, **kwargs) -> ToolResult:
        """Execute a tool by FQN safely."""
        pass
