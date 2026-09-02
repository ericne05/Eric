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
    - Providers, Router, Services, Builders, Managers.

    LLMRouter is the ONLY routing/failover authority.
    LLMService delegates all provider calls to LLMRouter.
    DummyProvider is registered as fallback ONLY when no real provider is available.
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
        from core.llm.router import LLMRouter
        from core.llm.providers.dummy import DummyProvider, DummyToolMapper

        from core.logger.interface import ILogger

        # Managers & Builders
        container.add_singleton(IModelRegistry, InMemoryModelRegistry)
        container.add_singleton(IConversationManager, InMemoryConversationManager)
        container.add_singleton(ITokenBudgetManager, TokenBudgetManager)
        container.add_singleton(IContextAssembler, ContextAssembler)
        container.add_singleton(IPromptBuilder, ReActPromptBuilder)
        container.add_singleton(IToolSchemaMapper, DummyToolMapper)

        # LLMRouter — the ONLY routing/failover authority
        def _router_factory(c):
            router = LLMRouter()
            # Try to register real Gemini provider (priority=10)
            try:
                from core.llm.providers.gemini import GeminiProvider
                router.register("gemini", GeminiProvider(), priority=10, capabilities=["chat", "goal"])
            except Exception:
                pass  # Not available in this environment
            # DummyProvider as fallback (priority=100, only used if real providers fail)
            dummy = DummyProvider(mapper=c.resolve(IToolSchemaMapper))
            router.register("dummy", dummy, priority=100, capabilities=["chat", "goal"])
            return router

        container.add_singleton(LLMRouter, _router_factory)

        # ILLMProvider — exposes the router's primary provider for legacy/test compatibility
        # NOTE: Application code should resolve LLMRouter, not ILLMProvider, for routing.
        def _provider_factory(c):
            router = c.resolve(LLMRouter)
            available = router.get_available_providers()
            if available:
                return available[0].provider
            return DummyProvider(mapper=c.resolve(IToolSchemaMapper))
        container.add_singleton(ILLMProvider, _provider_factory)

        # Telemetry is provided by ToolSystemModule
        from core.telemetry.interfaces import ITelemetryManager

        # LLMService — uses LLMRouter as the routing authority via the router
        def _service_factory(c):
            return LLMService(
                router=c.resolve(LLMRouter),
                model_registry=c.resolve(IModelRegistry),
                budget_manager=c.resolve(ITokenBudgetManager),
                telemetry=c.resolve(ITelemetryManager),
                logger=c.resolve(ILogger)
            )
        container.add_singleton(ILLMService, _service_factory)

        # Initialize model registry: real provider default preferred, dummy as fallback only
        registry = container.resolve(IModelRegistry)
        has_real_provider = False
        try:
            from core.llm.providers.gemini import GeminiProvider
            registry.register(
                ModelConfig(name=GeminiProvider.DEFAULT_MODEL, provider="gemini"),
                is_default=True,
            )
            has_real_provider = True
        except Exception:
            pass

        try:
            from core.llm.providers.openai_provider import OpenAIProvider
            registry.register(
                ModelConfig(name=OpenAIProvider.DEFAULT_MODEL, provider="openai"),
                is_default=not has_real_provider,
            )
            if not has_real_provider:
                has_real_provider = True
        except Exception:
            pass

        try:
            from core.llm.providers.claude_provider import ClaudeProvider
            registry.register(
                ModelConfig(name=ClaudeProvider.DEFAULT_MODEL, provider="claude"),
                is_default=not has_real_provider,
            )
            if not has_real_provider:
                has_real_provider = True
        except Exception:
            pass

        # DummyProvider model registered as explicit test/dev fallback, never implicit default when real provider exists
        registry.register(
            ModelConfig(name="dummy-v1", provider="dummy"),
            is_default=not has_real_provider,
        )
