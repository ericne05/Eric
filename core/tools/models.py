"""
Tool System Models.
"""

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Generator


from core.tools.enums import ToolPermission, ToolStatus


@dataclass
class ToolParameter:
    """
    Metadata for a single tool parameter.
    """
    name: str
    type_name: str
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolSchema:
    """
    Complete metadata for a Tool. Maps to LLM Function Calling Schema.
    """
    namespace: str
    name: str
    description: str
    version: str = "1.0.0"
    api_version: int = 1
    
    # Metadata for execution & marketplace
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    timeout_seconds: int = 30
    author: str = "Eric Team"
    permissions: list[ToolPermission] = field(default_factory=list)
    
    # Input parameters
    parameters: list[ToolParameter] = field(default_factory=list)
    
    @property
    def fqn(self) -> str:
        """Fully Qualified Name."""
        return f"{self.namespace}.{self.name}"


@dataclass
class ToolResult:
    """
    Standardized result from a Tool execution.
    """
    status: ToolStatus
    data: Any | Generator | AsyncGenerator | None = None
    error_message: str | None = None
