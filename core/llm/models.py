"""
LLM Subsystem Models.
"""

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.llm.enums import FinishReason, MessageRole


@dataclass
class LLMToolCall:
    """
    A request from the LLM to call a specific tool.
    """
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMMessage:
    """
    Standard message object for LLM context.
    """
    role: MessageRole
    content: str | None = None
    name: str | None = None
    tool_calls: List[LLMToolCall] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    """
    Result returned by the LLM Provider.
    """
    content: str | None = None
    tool_calls: List[LLMToolCall] | None = None
    finish_reason: FinishReason = FinishReason.STOP
    token_usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    model_name: str = ""
    is_streaming: bool = False
    stream_generator: AsyncGenerator[str, None] | None = None


@dataclass
class ModelConfig:
    """
    Configuration for a specific LLM.
    """
    name: str
    provider: str
    max_tokens: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    fallback_model: str | None = None
    parameters: Dict[str, Any] = field(default_factory=dict)




@dataclass
class ContextData:
    task_id: str
    goal: str
    state: str
    memories: List[str] = field(default_factory=list)
