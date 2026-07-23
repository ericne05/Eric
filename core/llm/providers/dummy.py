from core.agents.models import CancellationToken
"""
Dummy LLM Provider for local testing.
"""

import asyncio
from typing import Any, Dict, List

from core.llm.enums import FinishReason, MessageRole
from core.llm.interfaces import ILLMProvider, IToolSchemaMapper
from core.llm.models import LLMMessage, LLMResponse, LLMToolCall, ModelConfig
from core.tools.models import ToolSchema


class DummyToolMapper(IToolSchemaMapper):
    def map_schema(self, schema: ToolSchema) -> Dict[str, Any]:
        """Simple mapping to a dictionary for testing."""
        return {
            "name": schema.fqn,
            "description": schema.description,
            "parameters": [p.name for p in schema.parameters]
        }


class DummyProvider(ILLMProvider):
    """
    A fake LLM that always calls 'dummy.search' once, then returns success.
    """
    def __init__(self, mapper: IToolSchemaMapper):
        self._mapper = mapper

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[ToolSchema] | None = None,
        model: ModelConfig | None = None,
        cancellation_token: CancellationToken | None = None,
        stream: bool = False
    ) -> LLMResponse:
        
        # Simulate network latency
        await asyncio.sleep(1.0)
        
        # Cancellation check
        if cancellation_token and cancellation_token.is_cancelled:
            return LLMResponse(finish_reason=FinishReason.ERROR)
        
        # If there's a tool response in history, we "finish"
        for msg in reversed(messages):
            if msg.role == MessageRole.TOOL:
                return LLMResponse(
                    content="The dummy search was successful and returned results.",
                    finish_reason=FinishReason.STOP,
                    token_usage={"total": 50},
                    model_name="dummy-v1"
                )
                
        # Otherwise, initiate a tool call
        return LLMResponse(
            tool_calls=[
                LLMToolCall(
                    id="call_123",
                    name="dummy.search",
                    arguments={"query": "Test"}
                )
            ],
            finish_reason=FinishReason.TOOL_CALLS,
            token_usage={"total": 30},
            model_name="dummy-v1"
        )
