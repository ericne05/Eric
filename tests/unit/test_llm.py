"""
Unit tests for the LLM Framework.
"""

import asyncio
import pytest

from core.agents.enums import TaskState
from core.agents.interfaces import ExecutionContext
from core.agents.models import CancellationToken, Task
from core.events.event_bus import EventBus
from core.llm.builders import ContextAssembler, ReActPromptBuilder
from core.llm.enums import FinishReason
from core.llm.managers.budget import TokenBudgetManager
from core.llm.managers.conversation import InMemoryConversationManager
from core.llm.managers.model_registry import InMemoryModelRegistry
from core.llm.models import LLMMessage, ModelConfig
from core.llm.providers.dummy import DummyProvider, DummyToolMapper
from core.telemetry.manager import InMemoryTelemetryManager
from core.llm.service import LLMService


# Mock context
class MockContext:
    def __init__(self):
        self.task = Task(id="t1", goal="Test Goal", agent_name="react_agent")
        self.event_bus = EventBus()
        class MockLogger:
            def info(self, msg): pass
            def debug(self, msg): pass
            def warning(self, msg): pass
            def error(self, msg): pass
            def exception(self, msg): pass
        self.logger = MockLogger()


def test_model_registry():
    registry = InMemoryModelRegistry()
    cfg = ModelConfig(name="test-model", provider="test")
    registry.register(cfg, is_default=True)
    
    assert registry.get_model("test-model") == cfg
    assert registry.get_default_model() == cfg


def test_conversation_manager():
    mgr = InMemoryConversationManager()
    msg = LLMMessage(role="user", content="Hello")
    mgr.append_message("thread1", msg)
    
    history = mgr.get_history("thread1")
    assert len(history) == 1
    assert history[0].content == "Hello"


def test_budget_manager():
    budget = TokenBudgetManager(max_tokens_per_thread=100)
    budget.record_usage("t1", 50)
    assert budget.check_budget("t1") is True
    
    budget.record_usage("t1", 60) # total 110
    assert budget.check_budget("t1") is False


def test_prompt_builder():
    context = MockContext()
    assembler = ContextAssembler()
    builder = ReActPromptBuilder()
    
    ctx_data = assembler.assemble(context)
    history = [LLMMessage(role="user", content="Hi")]
    
    messages = builder.build_prompt(ctx_data, history)
    
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert "Test Goal" in messages[0].content
    assert messages[1].role == "user"


def test_dummy_provider_cancellation():
    mapper = DummyToolMapper()
    provider = DummyProvider(mapper)
    token = CancellationToken()
    
    # Pre-cancel
    token.cancel()
    
    response = asyncio.run(provider.generate(messages=[], cancellation_token=token))
    assert response.finish_reason == FinishReason.ERROR


def test_llm_service_budget_enforcement():
    registry = InMemoryModelRegistry()
    registry.register(ModelConfig(name="dummy", provider="dummy"), is_default=True)
    
    budget = TokenBudgetManager(max_tokens_per_thread=20) # Low budget
    mapper = DummyToolMapper()
    provider = DummyProvider(mapper)
    
    class MockLogger:
        def info(self, msg): pass
        def debug(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): pass
        
    service = LLMService(provider, registry, budget, InMemoryTelemetryManager(MockLogger()), MockLogger())
    
    # First call will consume 30 tokens from DummyProvider
    response = asyncio.run(service.generate(messages=[]))
    
    # Should fail because 30 > 20
    assert response.finish_reason == FinishReason.ERROR
