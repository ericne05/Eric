"""
Unit tests for core.events (Event and EventBus).
"""

import asyncio
from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest
from core.events import Event, EventBus, EventBusError, InvalidEventError


class TestEvent:
    """Unit tests for the Event dataclass."""

    def test_create_event_success(self) -> None:
        event = Event.create(
            name="system.ready",
            source="core.kernel",
            payload={"key": "val"},
            metadata={"meta": "data"},
        )
        assert isinstance(event.id, UUID)
        assert event.name == "system.ready"
        assert event.source == "core.kernel"
        assert event.payload == {"key": "val"}
        assert event.metadata == {"meta": "data"}

    def test_event_immutability(self) -> None:
        event = Event.create(name="system.ready", source="core.kernel")
        with pytest.raises(FrozenInstanceError):
            event.name = "system.shutdown"  # type: ignore

    def test_invalid_event_name_raises(self) -> None:
        with pytest.raises(InvalidEventError):
            Event.create(name="", source="core.kernel")

        with pytest.raises(InvalidEventError):
            Event.create(name="no_dot_name", source="core.kernel")

    def test_invalid_event_source_raises(self) -> None:
        with pytest.raises(InvalidEventError):
            Event.create(name="system.ready", source="")

    def test_event_defaults(self) -> None:
        event = Event(name="agent.browser.started", source="tools.browser")
        assert event.payload == {}
        assert event.metadata == {}
        assert event.correlation_id is None


class TestEventBus:
    """Unit tests for EventBus functionality."""

    def test_subscribe_and_publish_sync(self) -> None:
        bus = EventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("system.ready", handler)
        event = Event.create(name="system.ready", source="test")
        bus.publish_sync(event)

        assert len(received) == 1
        assert received[0] is event

    def test_subscribe_and_publish_async(self) -> None:
        bus = EventBus()
        received: list[Event] = []

        async def async_handler(event: Event) -> None:
            await asyncio.sleep(0.001)
            received.append(event)

        bus.subscribe("agent.browser.started", async_handler)
        event = Event.create(name="agent.browser.started", source="browser")

        async def run_test() -> None:
            await bus.publish(event)

        asyncio.run(run_test())

        assert len(received) == 1
        assert received[0] is event

    def test_wildcard_matching(self) -> None:
        bus = EventBus()
        received: list[str] = []

        def handle_all(event: Event) -> None:
            received.append(f"all:{event.name}")

        def handle_system(event: Event) -> None:
            received.append(f"sys:{event.name}")

        bus.subscribe("*", handle_all)
        bus.subscribe("system.*", handle_system)

        bus.publish_sync(Event.create(name="system.ready", source="test"))
        bus.publish_sync(Event.create(name="agent.browser.started", source="test"))

        assert "all:system.ready" in received
        assert "sys:system.ready" in received
        assert "all:agent.browser.started" in received
        assert "sys:agent.browser.started" not in received

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("system.ready", handler)
        bus.unsubscribe("system.ready", handler)

        bus.publish_sync(Event.create(name="system.ready", source="test"))
        assert len(received) == 0

    def test_handler_exception_isolation(self) -> None:
        bus = EventBus()
        successful_calls: list[str] = []

        def failing_handler(event: Event) -> None:
            raise RuntimeError("Handler failed!")

        def working_handler(event: Event) -> None:
            successful_calls.append("ok")

        bus.subscribe("system.ready", failing_handler)
        bus.subscribe("system.ready", working_handler)

        bus.publish_sync(Event.create(name="system.ready", source="test"))
        assert len(successful_calls) == 1

    def test_has_subscribers(self) -> None:
        bus = EventBus()
        assert not bus.has_subscribers("system.ready")

        def handler(event: Event) -> None:
            pass

        bus.subscribe("system.*", handler)
        assert bus.has_subscribers("system.ready")
        assert not bus.has_subscribers("agent.browser.started")

    def test_event_history(self) -> None:
        bus = EventBus(history_limit=2)
        e1 = Event.create(name="system.start", source="test")
        e2 = Event.create(name="system.ready", source="test")
        e3 = Event.create(name="system.shutdown", source="test")

        bus.publish_sync(e1)
        bus.publish_sync(e2)
        bus.publish_sync(e3)

        assert len(bus.history) == 2
        assert bus.history[0] is e2
        assert bus.history[1] is e3

    def test_clear_and_shutdown(self) -> None:
        bus = EventBus()

        def handler(event: Event) -> None:
            pass

        bus.subscribe("system.ready", handler)
        bus.publish_sync(Event.create(name="system.ready", source="test"))

        assert len(bus.history) == 1
        bus.shutdown()
        assert len(bus.history) == 0
        assert not bus.has_subscribers("system.ready")

    def test_invalid_subscribe_raises(self) -> None:
        bus = EventBus()
        with pytest.raises(EventBusError):
            bus.subscribe("", lambda e: None)

        with pytest.raises(EventBusError):
            bus.subscribe("system.ready", "not_a_callable")  # type: ignore
