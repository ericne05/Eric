"""
LLM System Module.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule
from core.llm.models import ModelConfig

if TYPE_CHECKING:
    from core.di.container import Container


class LLMSystemModule(IDependencyModule):
    """
    Registers the entire LLM Framework:
    - Providers, Services, Builders, Managers.
    """

    def register(self, container: "Container") -> None:
        from core.llm.interfaces import (
            IContextAssembler,
            IConversationManager,
            ILLMProvider,
            ILLMService,
            IModelRegistry,
            IPromptBuilder,
            ITokenBudgetManager,
            IToolSchemaMapper,
        )
        from core.llm.managers.budget import TokenBudgetManager
        from core.llm.managers.conversation import InMemoryConversationManager
        from core.llm.managers.model_registry import InMemoryModelRegistry
        from core.llm.builders import ContextAssembler, ReActPromptBuilder
        from core.llm.service import LLMService
        from core.llm.providers.dummy import DummyProvider, DummyToolMapper
        
        from core.logger.interface import ILogger

        # Managers & Builders
        container.add_singleton(IModelRegistry, InMemoryModelRegistry)
        container.add_singleton(IConversationManager, InMemoryConversationManager)
        container.add_singleton(ITokenBudgetManager, TokenBudgetManager)
        container.add_singleton(IContextAssembler, ContextAssembler)
        container.add_singleton(IPromptBuilder, ReActPromptBuilder)
        container.add_singleton(IToolSchemaMapper, DummyToolMapper)
        
        # Providers
        def _provider_factory(c):
            try:
                from core.llm.providers.gemini import GeminiProvider
                return GeminiProvider()
            except Exception:
                return DummyProvider(mapper=c.resolve(IToolSchemaMapper))
        container.add_singleton(ILLMProvider, _provider_factory)

        # Telemetry is provided by ToolSystemModule, but we can resolve it
        from core.telemetry.interfaces import ITelemetryManager

        # Register Service
        def _service_factory(c):
            return LLMService(
                provider=c.resolve(ILLMProvider),
                model_registry=c.resolve(IModelRegistry),
                budget_manager=c.resolve(ITokenBudgetManager),
                telemetry=c.resolve(ITelemetryManager),
                logger=c.resolve(ILogger)
            )
        container.add_singleton(ILLMService, _service_factory)
        
        # Initialize default model
        registry = container.resolve(IModelRegistry)
        registry.register(ModelConfig(name="dummy-v1", provider="dummy"), is_default=True)
