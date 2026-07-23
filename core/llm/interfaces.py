from core.agents.models import CancellationToken
"""
LLM Subsystem Interfaces.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from core.agents.interfaces import ExecutionContext
from core.llm.models import LLMMessage, LLMResponse, ModelConfig
from core.tools.models import ToolSchema


class ILLMProvider(ABC):
    """
    Adapter for a specific LLM Provider (OpenAI, Gemini, Ollama, etc.).
    """
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[ToolSchema] | None = None,
        model: ModelConfig | None = None,
        cancellation_token: CancellationToken | None = None,
        stream: bool = False
    ) -> LLMResponse:
        """Call the LLM API and return the response."""
        pass


class ILLMService(ABC):
    """
    Orchestrator for LLM generation.
    Handles retry, timeout, telemetry, fallback, and cancellation.
    """
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[ToolSchema] | None = None,
        cancellation_token: CancellationToken | None = None,
        stream: bool = False
    ) -> LLMResponse:
        """Generate response via the configured provider."""
        pass


class IModelRegistry(ABC):
    """
    Registry for managing ModelConfigs.
    """
    @abstractmethod
    def register(self, config: ModelConfig) -> None:
        pass

    @abstractmethod
    def get_model(self, name: str) -> ModelConfig | None:
        pass

    @abstractmethod
    def get_default_model(self) -> ModelConfig:
        pass


class IConversationManager(ABC):
    """
    Manages LLM message histories for different sessions/threads.
    """
    @abstractmethod
    def append_message(self, thread_id: str, message: LLMMessage) -> None:
        pass

    @abstractmethod
    def get_history(self, thread_id: str) -> List[LLMMessage]:
        pass

    @abstractmethod
    def clear(self, thread_id: str) -> None:
        pass


class IContextAssembler(ABC):
    """
    Collects execution context and environment data to be built into the prompt.
    """
    @abstractmethod
    def assemble(self, context: ExecutionContext) -> Dict[str, Any]:
        """Returns a unified data dict containing goal, memory, system state."""
        pass


class IPromptBuilder(ABC):
    """
    Builds the final list of LLMMessages for the LLMService.
    """
    @abstractmethod
    def build_prompt(self, context_data: Dict[str, Any], history: List[LLMMessage]) -> List[LLMMessage]:
        pass


class IToolSchemaMapper(ABC):
    """
    Maps the generic ToolSchema to provider-specific formats.
    """
    @abstractmethod
    def map_schema(self, schema: ToolSchema) -> Dict[str, Any]:
        pass


class ITokenBudgetManager(ABC):
    """
    Tracks and limits token consumption.
    """
    @abstractmethod
    def record_usage(self, thread_id: str, tokens: int, cost: float = 0.0) -> None:
        pass

    @abstractmethod
    def check_budget(self, thread_id: str) -> bool:
        """Returns True if within budget. False if budget exceeded."""
        pass
