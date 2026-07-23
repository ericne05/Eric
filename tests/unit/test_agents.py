"""
Unit tests for the Agent Runtime (Sprint 8).
"""

from dataclasses import dataclass
from typing import Any

import pytest

from core.agents.enums import StepType, TaskState
from core.agents.interfaces import ExecutionContext, IAgent
from core.agents.models import Step, Task
from core.agents.registry import AgentRegistry
from core.agents.runtime import AgentRuntime
from core.config.schemas import SystemConfig
from core.events.event_bus import EventBus
from core.logger.interface import ILogger
from core.memory.interfaces import IMemoryService


class MockLogger(ILogger):
    def debug(self, msg: str, **kwargs) -> None: pass
    def info(self, msg: str, **kwargs) -> None: pass
    def warning(self, msg: str, **kwargs) -> None: pass
    def error(self, msg: str, exc_info=None, **kwargs) -> None: pass
    def exception(self, msg: str, exc_info=None, **kwargs) -> None: pass
    def critical(self, msg: str, exc_info=None, **kwargs) -> None: pass
    def shutdown(self) -> None: pass
    def bind(self, **kwargs) -> "ILogger": return self


class MockMemory(IMemoryService):
    def store(self, entry: Any) -> None: pass
    def recall(self, query: str, top_k: int = 5) -> list[Any]: return []
    def get_recent(self, n: int = 10) -> list[Any]: return []
    def clear_short_term(self) -> None: pass


class FailAgent(IAgent):
    @property
    def name(self) -> str: return "fail_agent"

    def plan(self, context: ExecutionContext) -> str | None:
        raise ValueError("Simulated failure in plan")

    def act(self, context: ExecutionContext, thought: str) -> Any: pass
    def observe(self, context: ExecutionContext, action_result: Any) -> str: pass


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        agent = FailAgent()
        
        registry.register(agent)
        assert registry.get_agent("fail_agent") is agent
        
        with pytest.raises(ValueError):
            registry.register(agent)  # Duplicate
            
        assert len(registry.get_all()) == 1


class TestAgentRuntime:
    @pytest.fixture
    def setup_runtime(self):
        registry = AgentRegistry()
        
        # Register DummyAgent
        from core.agents.dummy import DummyAgent
        registry.register(DummyAgent())
        registry.register(FailAgent())
        
        logger = MockLogger()
        event_bus = EventBus()
        config = SystemConfig()
        memory = MockMemory()
        
        runtime = AgentRuntime(registry, logger, event_bus, config, memory)
        return runtime, event_bus

    def test_submit_task_emits_event(self, setup_runtime):
        runtime, event_bus = setup_runtime
        events_emitted = []
        event_bus.subscribe("task.created", lambda e: events_emitted.append(e))
        
        task = Task(id="t1", goal="Test Task")
        runtime.submit_task(task)
        
        assert task.state == TaskState.PENDING
        assert len(events_emitted) == 1
        assert events_emitted[0].payload["task_id"] == "t1"

    def test_process_queue_dummy_agent(self, setup_runtime):
        runtime, event_bus = setup_runtime
        
        task = Task(id="t1", goal="Open YouTube")
        # dummy_agent is the default if not specified
        runtime.submit_task(task)
        
        runtime.process_queue()
        
        assert task.state == TaskState.COMPLETED
        # DummyAgent loops 2 times, each loop has Thought, Action, Observation. Total 6 steps.
        assert len(task.steps) == 6
        assert task.steps[0].type == StepType.THOUGHT
        assert task.steps[1].type == StepType.ACTION
        assert task.steps[2].type == StepType.OBSERVATION
        
        assert task.result == "Video playing"

    def test_agent_failure(self, setup_runtime):
        runtime, event_bus = setup_runtime
        
        task = Task(id="t1", goal="Fail me", agent_name="fail_agent")
        runtime.submit_task(task)
        
        runtime.process_queue()
        
        assert task.state == TaskState.FAILED
        assert "Simulated failure" in task.result

    def test_cancel_task(self, setup_runtime):
        runtime, event_bus = setup_runtime
        
        task = Task(id="t1", goal="Cancel me")
        runtime.submit_task(task)
        
        runtime.cancel_task("t1")
        assert task.state == TaskState.CANCELLED
        
        # Processing should skip cancelled tasks immediately
        runtime.process_queue()
        assert task.state == TaskState.CANCELLED
        assert len(task.steps) == 0
