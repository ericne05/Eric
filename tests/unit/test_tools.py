"""
Unit tests for Tool System.
"""

import asyncio
import pytest

from core.agents.models import Task
from core.events.event_bus import EventBus
from core.tools.decorator import tool
from core.tools.enums import ToolPermission, ToolStatus
from core.tools.executor import ToolExecutor
from core.tools.registry import ToolRegistry


# Mock classes
class MockPolicyEngine:
    def check_permission(self, context, tool_fqn):
        from core.security.enums import PolicyDecision
        return PolicyDecision.ALLOW
        
    def evaluate_action(self, tool, context):
        from core.security.enums import PolicyDecision
        class MockResult:
            def __init__(self):
                self.decision = PolicyDecision.ALLOW
        return MockResult()

class MockTelemetry:
    def trace(self, name):
        import contextlib
        @contextlib.contextmanager
        def dummy_context():
            yield None
        return dummy_context()
        
    def record_event(self, name: str, attributes: dict = None) -> None:
        pass

class MockContext:
    def __init__(self):
        self.task = Task(id="t1", goal="Test", agent_name="test")
        self.event_bus = EventBus()
        self.trace_id = "trace-123"
        class MockLogger:
            def info(self, msg): pass
            def debug(self, msg): pass
            def warning(self, msg): pass
            def error(self, msg): pass
            def exception(self, msg): pass
        self.logger = MockLogger()


# Define some tools
@tool(namespace="test", name="sync_tool", description="A sync tool")
def sync_tool(context, val: int) -> int:
    return val * 2


@tool(namespace="test", name="async_tool", timeout_seconds=1)
async def async_tool(context, delay: float):
    await asyncio.sleep(delay)
    return "done"


@tool(namespace="test", name="stream_tool")
async def stream_tool(context):
    yield 1
    yield 2


def test_tool_decorator():
    schema = sync_tool.schema
    assert schema.namespace == "test"
    assert schema.name == "sync_tool"
    assert schema.fqn == "test.sync_tool"
    assert len(schema.parameters) == 1
    assert schema.parameters[0].name == "val"
    assert schema.parameters[0].type_name == "int"


def test_registry_conflict():
    registry = ToolRegistry()
    registry.register(sync_tool)
    
    with pytest.raises(ValueError, match="Tool conflict"):
        registry.register(sync_tool)


def test_executor_sync_tool():
    registry = ToolRegistry()
    registry.register(sync_tool)
    executor = ToolExecutor(registry, MockPolicyEngine(), MockTelemetry())
    context = MockContext()
    
    result = asyncio.run(executor.execute_tool(context, "test.sync_tool", val=5))
    assert result.status == ToolStatus.SUCCESS
    assert result.data == 10


def test_executor_timeout():
    registry = ToolRegistry()
    registry.register(async_tool)
    executor = ToolExecutor(registry, MockPolicyEngine(), MockTelemetry())
    context = MockContext()
    
    # Tool has 1s timeout, delay is 2s
    result = asyncio.run(executor.execute_tool(context, "test.async_tool", delay=2.0))
    assert result.status == ToolStatus.TIMEOUT
    assert "timed out" in result.error_message


def test_executor_streaming():
    registry = ToolRegistry()
    registry.register(stream_tool)
    executor = ToolExecutor(registry, MockPolicyEngine(), MockTelemetry())
    context = MockContext()
    
    result = asyncio.run(executor.execute_tool(context, "test.stream_tool"))
    assert result.status == ToolStatus.SUCCESS
    
    async def _collect():
        items = []
        async for item in result.data:
            items.append(item)
        return items
        
    items = asyncio.run(_collect())
    assert items == [1, 2]
