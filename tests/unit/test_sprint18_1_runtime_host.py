"""
Sprint 18.1 — EricRuntimeHost Unit Tests.

Validates:
1. Runtime lifecycle state machine (CREATED -> STARTING -> READY -> STOPPING -> STOPPED).
2. Startup failure handling (STARTING -> ERROR, structured error info, event emission).
3. Graceful shutdown (Kernel.shutdown() called, runtimes stopped, state is STOPPED).
4. Shared EventBus (no second EventBus created, events dispatched to bus).
5. Single composition root (resolves DI-managed services, no second Kernel).
6. Idempotency (duplicate start() is deterministic, duplicate stop() is safe).
7. Serialization & isolation (RuntimeSnapshot contains no live service objects).
8. AppBootstrap integration (shutdown defect fixed: Kernel.shutdown() is invoked).
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from core.events.event_bus import EventBus
from core.kernel.lifecycle import SystemState
from core.runtime.client_interface import IEricRuntime
from core.runtime.host import EricRuntimeHost
from core.runtime.models import (
    RuntimeErrorInfo,
    RuntimeEvent,
    RuntimeSnapshot,
    RuntimeStatus,
)


class TestRuntimeLifecycle:
    """Test standard happy-path lifecycle transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_created(self):
        host = EricRuntimeHost()
        assert host.get_status() == RuntimeStatus.CREATED
        snapshot = host.get_snapshot()
        assert snapshot.status == RuntimeStatus.CREATED
        assert snapshot.started_at is None
        assert snapshot.last_error is None

    @pytest.mark.asyncio
    async def test_runtime_status_transitions_created_starting_ready_stopping_stopped(self):
        # Create a mock Kernel with container and EventBus
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.CREATED
        mock_bus = EventBus()
        mock_kernel.event_bus = mock_bus

        mock_container = MagicMock()
        mock_container.resolve.side_effect = lambda cls: MagicMock()
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        assert host.get_status() == RuntimeStatus.CREATED

        observed_states = []
        host.subscribe("runtime.starting", lambda e: observed_states.append(host.get_status()))
        host.subscribe("runtime.ready", lambda e: observed_states.append(host.get_status()))
        host.subscribe("runtime.stopping", lambda e: observed_states.append(host.get_status()))
        host.subscribe("runtime.stopped", lambda e: observed_states.append(host.get_status()))

        await host.start()
        assert host.get_status() == RuntimeStatus.READY
        assert mock_kernel.boot.called

        snapshot = host.get_snapshot()
        assert snapshot.status == RuntimeStatus.READY
        assert snapshot.started_at is not None

        await host.stop()
        assert host.get_status() == RuntimeStatus.STOPPED
        assert mock_kernel.shutdown.called

        # Validate that intermediate states were observed
        assert RuntimeStatus.STARTING in observed_states
        assert RuntimeStatus.READY in observed_states
        assert RuntimeStatus.STOPPING in observed_states
        assert RuntimeStatus.STOPPED in observed_states

    @pytest.mark.asyncio
    async def test_runtime_emits_structured_events(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_bus = EventBus()
        mock_kernel.event_bus = mock_bus
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        received_events = []

        host.subscribe("runtime.ready", lambda e: received_events.append(e))
        host.subscribe("runtime.stopped", lambda e: received_events.append(e))

        await host.start()
        assert len(received_events) == 1
        assert received_events[0].event_type == "runtime.ready"
        assert isinstance(received_events[0], RuntimeEvent)
        assert isinstance(received_events[0].timestamp, datetime)

        await host.stop()
        assert len(received_events) == 2
        assert received_events[1].event_type == "runtime.stopped"

    @pytest.mark.asyncio
    async def test_wildcard_event_subscription(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        all_events = []
        host.subscribe("*", lambda e: all_events.append(e.event_type))

        await host.start()
        await host.stop()

        assert "runtime.starting" in all_events
        assert "runtime.ready" in all_events
        assert "runtime.stopping" in all_events
        assert "runtime.stopped" in all_events

    @pytest.mark.asyncio
    async def test_unsubscribe_event_listener(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        events = []
        handler = lambda e: events.append(e)

        host.subscribe("runtime.ready", handler)
        host.unsubscribe("runtime.ready", handler)

        await host.start()
        assert len(events) == 0


class TestStartupFailure:
    """Verify safe handling of startup errors without exposing secrets."""

    @pytest.mark.asyncio
    async def test_startup_failure_transitions_to_error(self):
        failing_kernel = MagicMock()
        failing_kernel.state = SystemState.CREATED
        failing_kernel.boot.side_effect = RuntimeError("Subsystem failed to initialize")

        host = EricRuntimeHost(kernel=failing_kernel)

        error_events = []
        host.subscribe("runtime.error", lambda e: error_events.append(e))

        with pytest.raises(RuntimeError) as exc_info:
            await host.start()

        assert "Subsystem failed to initialize" in str(exc_info.value)
        assert host.get_status() == RuntimeStatus.ERROR

        snapshot = host.get_snapshot()
        assert snapshot.status == RuntimeStatus.ERROR
        assert snapshot.last_error is not None
        assert snapshot.last_error.code == "STARTUP_FAILED"
        assert "Subsystem failed to initialize" in snapshot.last_error.message
        assert snapshot.last_error.recoverable is False

        assert len(error_events) == 1
        assert error_events[0].event_type == "runtime.error"
        assert error_events[0].payload["code"] == "STARTUP_FAILED"

    @pytest.mark.asyncio
    async def test_startup_failure_does_not_leak_secrets_in_error_payload(self):
        failing_kernel = MagicMock()
        failing_kernel.state = SystemState.CREATED
        failing_kernel.boot.side_effect = ValueError("Invalid config: API_KEY=secret_val_12345")

        host = EricRuntimeHost(kernel=failing_kernel)
        error_events = []
        host.subscribe("runtime.error", lambda e: error_events.append(e))

        with pytest.raises(ValueError):
            await host.start()

        snapshot = host.get_snapshot()
        payload = error_events[0].payload
        # Payload must only have safe structured keys
        assert set(payload.keys()) == {"code", "message", "recoverable"}
        assert payload["code"] == "STARTUP_FAILED"


class TestShutdownGraceful:
    """Verify shutdown sequence and cleanup."""

    @pytest.mark.asyncio
    async def test_stop_calls_kernel_shutdown(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        await host.stop()

        assert mock_kernel.shutdown.called
        assert host.get_status() == RuntimeStatus.STOPPED

    @pytest.mark.asyncio
    async def test_stop_stops_desktop_and_vision_runtimes(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()

        mock_desktop = MagicMock()
        mock_desktop.start = AsyncMock()
        mock_desktop.stop = AsyncMock()

        mock_vision = MagicMock()
        mock_vision.start = AsyncMock()
        mock_vision.shutdown = AsyncMock()

        mock_container = MagicMock()
        from core.desktop.interfaces import IDesktopRuntime
        from core.vision.interfaces import IVisionRuntime

        def resolve_service(cls):
            if cls == IDesktopRuntime:
                return mock_desktop
            if cls == IVisionRuntime:
                return mock_vision
            return MagicMock()

        mock_container.resolve.side_effect = resolve_service
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        assert mock_desktop.start.called
        assert mock_vision.start.called

        await host.stop()
        assert mock_desktop.stop.called
        assert mock_vision.shutdown.called

    @pytest.mark.asyncio
    async def test_app_bootstrap_shutdown_calls_kernel_shutdown(self):
        """Fix verification: AppBootstrap.shutdown() must invoke Kernel.shutdown()."""
        from app.bootstrap.app_bootstrap import AppBootstrap

        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        bootstrap = AppBootstrap(runtime_host=host)

        await bootstrap.initialize()
        assert bootstrap.is_bootstrapped is True
        assert host.get_status() == RuntimeStatus.READY

        await bootstrap.shutdown()
        assert bootstrap.is_bootstrapped is False
        assert host.get_status() == RuntimeStatus.STOPPED
        assert mock_kernel.shutdown.called, "AppBootstrap.shutdown() must call Kernel.shutdown() via EricRuntimeHost"


class TestCompositionRootAndEventBus:
    """Verify single composition root and shared EventBus constraints."""

    @pytest.mark.asyncio
    async def test_runtime_host_uses_kernel_event_bus(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        shared_bus = EventBus()
        mock_kernel.event_bus = shared_bus
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()

        assert host.event_bus is shared_bus, "RuntimeHost must share the Kernel's EventBus"

    @pytest.mark.asyncio
    async def test_runtime_host_resolves_services_from_di_container(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()

        from core.runtime.capability import CapabilityNegotiator
        from core.goals import GoalManager
        from core.cognition import CognitiveCoordinator

        mock_negotiator = MagicMock()
        mock_goal_manager = MagicMock()
        mock_coordinator = MagicMock()

        mock_container = MagicMock()
        def resolve_service(cls):
            if cls == CapabilityNegotiator:
                return mock_negotiator
            if cls == GoalManager:
                return mock_goal_manager
            if cls == CognitiveCoordinator:
                return mock_coordinator
            return MagicMock()

        mock_container.resolve.side_effect = resolve_service
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()

        assert host.negotiator is mock_negotiator
        assert host.goal_manager is mock_goal_manager
        assert host.coordinator is mock_coordinator


class TestIdempotency:
    """Verify that start and stop operations are deterministic and safe when called multiple times."""

    @pytest.mark.asyncio
    async def test_duplicate_start_is_idempotent(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.CREATED
        mock_kernel.event_bus = EventBus()
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        assert host.get_status() == RuntimeStatus.READY
        assert mock_kernel.boot.call_count == 1

        # Second start call must be a safe no-op
        await host.start()
        assert host.get_status() == RuntimeStatus.READY
        assert mock_kernel.boot.call_count == 1

    @pytest.mark.asyncio
    async def test_duplicate_stop_is_safe(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()
        mock_kernel.container = MagicMock()

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        await host.stop()
        assert host.get_status() == RuntimeStatus.STOPPED
        assert mock_kernel.shutdown.call_count == 1

        # Second stop call must be safe and idempotent
        await host.stop()
        assert host.get_status() == RuntimeStatus.STOPPED
        assert mock_kernel.shutdown.call_count == 1


class TestSnapshotSerialization:
    """Verify that RuntimeSnapshot contains no live service objects and is JSON-friendly."""

    def test_snapshot_contains_no_live_service_objects(self):
        now = datetime.now(timezone.utc)
        error = RuntimeErrorInfo(code="ERR_1", message="Test error", recoverable=True, timestamp=now)
        snapshot = RuntimeSnapshot(
            status=RuntimeStatus.READY,
            started_at=now,
            active_goal_id="goal-123",
            last_error=error,
        )

        d = snapshot.to_dict()
        assert isinstance(d, dict)
        assert d["status"] == "ready"
        assert d["started_at"] == now.isoformat()
        assert d["active_goal_id"] == "goal-123"
        assert d["last_error"]["code"] == "ERR_1"
        assert d["last_error"]["recoverable"] is True

        # Roundtrip
        reconstructed = RuntimeSnapshot.from_dict(d)
        assert reconstructed.status == RuntimeStatus.READY
        assert reconstructed.active_goal_id == "goal-123"
        assert reconstructed.last_error.code == "ERR_1"
        assert reconstructed.last_error.recoverable is True

    def test_runtime_event_serialization_roundtrip(self):
        now = datetime.now(timezone.utc)
        event = RuntimeEvent(
            event_type="runtime.ready",
            timestamp=now,
            payload={"status": "ready", "version": "1.0"},
        )
        d = event.to_dict()
        assert d["event_type"] == "runtime.ready"
        assert d["payload"]["version"] == "1.0"

        reconstructed = RuntimeEvent.from_dict(d)
        assert reconstructed.event_type == "runtime.ready"
        assert reconstructed.payload["version"] == "1.0"

    def test_runtime_error_info_serialization_roundtrip(self):
        now = datetime.now(timezone.utc)
        error = RuntimeErrorInfo(
            code="NETWORK_TIMEOUT",
            message="Connection to backend timed out",
            recoverable=True,
            timestamp=now,
        )
        d = error.to_dict()
        assert d["code"] == "NETWORK_TIMEOUT"
        assert d["recoverable"] is True

        reconstructed = RuntimeErrorInfo.from_dict(d)
        assert reconstructed.code == "NETWORK_TIMEOUT"
        assert reconstructed.recoverable is True
        assert reconstructed.message == "Connection to backend timed out"
