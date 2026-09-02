"""
Dummy Agent Implementation for Sprint 8/9 testing.
"""

import asyncio
from typing import Any

from core.agents.interfaces import ExecutionContext, IAgent


class DummyAgent(IAgent):
    """
    A hardcoded mock agent that simulates the ReAct loop and uses the ToolExecutor.
    """

    def __init__(self):
        self._internal_state = 0

    @property
    def name(self) -> str:
        return "dummy_agent"

    def plan(self, context: ExecutionContext) -> str | None:
        """Return a thought based on the current state."""
        if self._internal_state == 0:
            return "Need to search using the dummy tool."
        else:
            return None  # Finished

    def act(self, context: ExecutionContext, thought: str) -> Any:
        """Call the ToolExecutor."""
        if self._internal_state == 0:
            # Run the async tool executor synchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If running inside pytest async or similar
                    import nest_asyncio
                    nest_asyncio.apply()
            except RuntimeError:
                pass
            
            result = asyncio.run(context.tool_executor.execute_tool(
                context, fqn="dummy.search", query=context.task.goal
            ))
            return result
        return "unknown_action"

    def observe(self, context: ExecutionContext, action_result: Any) -> str:
        """Return an observation and advance state."""
        self._internal_state += 1
        
        # action_result is a ToolResult
        if hasattr(action_result, "status"):
            # If it's a generator (streaming result)
            data = action_result.data
            
            if hasattr(data, '__aiter__'):
                # Collect async generator
                async def _collect():
                    items = []
                    async for item in data:
                        items.append(item)
                    return items
                collected = asyncio.run(_collect())
                context.task.result = f"Collected: {collected}"
            else:
                context.task.result = str(data)
                
            return f"Search success. Status: {action_result.status.value}"
        
        return "Action completed."
