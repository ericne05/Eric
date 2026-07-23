"""
Tool Decorator.
Converts Python functions into ITool instances.
"""

import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, Coroutine, TYPE_CHECKING

from core.tools.enums import ToolPermission, ToolStatus
from core.tools.interfaces import ITool
from core.tools.models import ToolParameter, ToolResult, ToolSchema

if TYPE_CHECKING:
    from core.agents.interfaces import ExecutionContext


class DecoratedTool(ITool):
    def __init__(self, schema: ToolSchema, func: Callable):
        self._schema = schema
        self._func = func
        self._is_coroutine = inspect.iscoroutinefunction(func)
        self._is_asyncgen = inspect.isasyncgenfunction(func)
        self._is_gen = inspect.isgeneratorfunction(func)

    @property
    def schema(self) -> ToolSchema:
        return self._schema

    async def execute_async(self, context: "ExecutionContext", cancellation_token: "CancellationToken | None" = None, **kwargs) -> ToolResult:
        """
        Executes the decorated function.
        Handles wrapping sync functions in threads if necessary, and adapts returns.
        """
        try:
            # Remove kwargs that are not in the function signature if any
            # For robustness.
            
            if self._is_coroutine:
                # Pass cancellation_token if requested by function
                sig = inspect.signature(self._func)
                if 'cancellation_token' in sig.parameters:
                    kwargs['cancellation_token'] = cancellation_token
                    
                result = await self._func(context, **kwargs)
                return ToolResult(status=ToolStatus.SUCCESS, data=result)
                
            elif self._is_asyncgen:
                # Return the async generator directly so the caller can stream it
                result = self._func(context, **kwargs)
                return ToolResult(status=ToolStatus.SUCCESS, data=result)
                
            elif self._is_gen:
                result = self._func(context, **kwargs)
                return ToolResult(status=ToolStatus.SUCCESS, data=result)
                
            else:
                # Sync function. In a real OS we might run this in a ThreadPoolExecutor
                # to avoid blocking the asyncio event loop.
                sig = inspect.signature(self._func)
                if 'cancellation_token' in sig.parameters:
                    kwargs['cancellation_token'] = cancellation_token
                    
                result = await asyncio.to_thread(self._func, context, **kwargs)
                return ToolResult(status=ToolStatus.SUCCESS, data=result)
                
        except Exception as e:
            # Let the executor catch and log this, we just re-raise or we could pack it in ERROR ToolResult.
            # But the contract is the executor handles exceptions, so we re-raise.
            raise e


def tool(
    namespace: str,
    name: str | None = None,
    description: str | None = None,
    version: str = "1.0.0",
    api_version: int = 1,
    category: str = "general",
    tags: list[str] | None = None,
    examples: list[str] | None = None,
    timeout_seconds: int = 30,
    author: str = "Eric Team",
    permissions: list[ToolPermission] | None = None,
):
    """
    Decorator to convert a Python function to an ITool.
    The function MUST accept `context: ExecutionContext` as its first argument.
    """
    def decorator(func: Callable) -> ITool:
        tool_name = name or func.__name__
        tool_desc = description or inspect.getdoc(func) or ""
        
        # Parse signature
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            if param_name == "context":
                continue  # Skip the context parameter
                
            param_type = param.annotation
            type_name = param_type.__name__ if hasattr(param_type, "__name__") else str(param_type)
            
            # This is a basic parser. In a real scenario, we might use pydantic for deep schema parsing.
            is_required = param.default == inspect.Parameter.empty
            
            parameters.append(ToolParameter(
                name=param_name,
                type_name=type_name,
                required=is_required,
                default=None if is_required else param.default
            ))
            
        schema = ToolSchema(
            namespace=namespace,
            name=tool_name,
            description=tool_desc,
            version=version,
            api_version=api_version,
            category=category,
            tags=tags or [],
            examples=examples or [],
            timeout_seconds=timeout_seconds,
            author=author,
            permissions=permissions or [],
            parameters=parameters
        )
        
        return DecoratedTool(schema, func)
        
    return decorator
