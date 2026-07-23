"""
Agent System Module Registration.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class AgentSystemModule(IDependencyModule):
    """
    Registers the AgentRuntime, AgentRegistry, and default agents.
    """

    def register(self, container: "Container") -> None:
        from core.agents.dummy import DummyAgent
        from core.agents.interfaces import IAgentRegistry, IAgentRuntime
        from core.agents.registry import AgentRegistry
        from core.agents.runtime import AgentRuntime

        # Register Subsystems
        container.add_singleton(IAgentRegistry, AgentRegistry)
        
        from core.logger.interface import ILogger
        from core.events.event_bus import EventBus
        from core.config.schemas import SystemConfig
        from core.memory.interfaces import IMemoryService
        from core.tools.interfaces import IToolExecutor

        def _runtime_factory(c):
            return AgentRuntime(
                registry=c.resolve(IAgentRegistry),
                logger=c.resolve(ILogger),
                event_bus=c.resolve(EventBus),
                config=c.resolve(SystemConfig),
                memory=c.resolve(IMemoryService),
                tool_executor=c.resolve(IToolExecutor),
            )
        container.add_singleton(IAgentRuntime, _runtime_factory)
        
        # Register default agents
        from core.agents.react import ReActAgent
        from core.llm.interfaces import ILLMService, IPromptBuilder, IContextAssembler, IConversationManager
        from core.tools.interfaces import IToolRegistry
        
        def _react_agent_factory(c):
            return ReActAgent(
                llm_service=c.resolve(ILLMService),
                prompt_builder=c.resolve(IPromptBuilder),
                context_assembler=c.resolve(IContextAssembler),
                conversation_manager=c.resolve(IConversationManager),
                tool_registry=c.resolve(IToolRegistry),
            )
        
        registry = container.resolve(IAgentRegistry)
        registry.register(_react_agent_factory(container))
