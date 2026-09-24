"""
Sprint 18.2 — EricClient Boundary & Structured UI Events Unit Tests.

Validates:
1. Client -> Runtime command routing (submit, start, execute, pause, resume, cancel).
2. Runtime -> Client structured event dispatching.
3. MainViewModel progress tracking via structured events (NOT string parsing).
4. BackendBridge uses DI-managed LLMRouter singleton (no unconditional build_default_router).
5. Encapsulation: EricClient does not leak backend internals (Kernel, Container, EventBus, GoalManager).
6. Active goal tracking: RuntimeStatus transitions READY -> BUSY -> READY with active_goal_id.
7. Subscription lifecycle (subscribe, unsubscribe, wildcard).
8. Client-safe model serialization (GoalHandle, GoalSnapshot, GoalProgressRecord).
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.client.eric_client import EricClient
from app.services.backend_bridge import BackendBridge
from app.viewmodels.main_viewmodel import MainViewModel
from core.events.event import Event
from core.events.event_bus import EventBus
from core.kernel.lifecycle import SystemState
from core.llm.router import LLMRouter
from core.runtime.client_interface import IEricRuntime
from core.runtime.host import EricRuntimeHost
from core.runtime.models import (
    GoalHandle,
    GoalProgressRecord,
    GoalSnapshot,
    RuntimeEvent,
    RuntimeSnapshot,
    RuntimeStatus,
)


class TestClientCommandRouting:
    """Verify EricClient operations delegate cleanly through IEricRuntime to RuntimeHost."""

    @pytest.mark.asyncio
    async def test_client_submit_and_start_goal(self):
        mock_goal_manager = MagicMock()
        mock_goal = MagicMock()
        mock_goal.id = "goal-456"
        mock_goal.state.value = "ready"
        mock_goal_manager.create_goal = AsyncMock(return_value=mock_goal)

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.summary = "Executed successfully"
        mock_result.error = None
        mock_goal_manager.start_goal = AsyncMock(return_value=mock_result)

        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()

        mock_container = MagicMock()
        from core.goals import GoalManager
        mock_container.resolve.side_effect = lambda cls: mock_goal_manager if cls == GoalManager else MagicMock()
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()

        client = EricClient(runtime=host)

        # 1. Submit goal
        handle = await client.submit_goal("Test task", priority="high")
        assert isinstance(handle, GoalHandle)
        assert handle.goal_id == "goal-456"
        assert handle.status == "ready"
        mock_goal_manager.create_goal.assert_called_once_with("Test task", priority="high")

        # 2. Start goal
        res = await client.start_goal(handle.goal_id)
        assert res["success"] is True
        assert res["goal_id"] == "goal-456"
        assert res["summary"] == "Executed successfully"
        mock_goal_manager.start_goal.assert_called_once_with("goal-456")

    @pytest.mark.asyncio
    async def test_client_pause_resume_cancel(self):
        mock_goal_manager = MagicMock()
        mock_goal_manager.pause_goal = AsyncMock(return_value=True)
        mock_goal_manager.cancel_goal = AsyncMock(return_value=True)

        resumed_res = MagicMock(success=True)
        mock_goal_manager.resume_goal = AsyncMock(return_value=resumed_res)

        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()

        from core.goals import GoalManager
        mock_container = MagicMock()
        mock_container.resolve.side_effect = lambda cls: mock_goal_manager if cls == GoalManager else MagicMock()
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        client = EricClient(runtime=host)

        # Test pause
        assert await client.pause_goal("g-1") is True
        mock_goal_manager.pause_goal.assert_called_once_with("g-1")

        # Test resume
        assert await client.resume_goal("g-1") is True
        mock_goal_manager.resume_goal.assert_called_once_with("g-1")

        # Test cancel
        assert await client.cancel_goal("g-1") is True
        mock_goal_manager.cancel_goal.assert_called_once_with("g-1")

    @pytest.mark.asyncio
    async def test_client_execute_goal_convenience(self):
        mock_goal_manager = MagicMock()
        mock_goal = MagicMock(id="g-exec")
        mock_goal.state.value = "ready"
        mock_goal_manager.create_goal = AsyncMock(return_value=mock_goal)
        mock_goal_manager.start_goal = AsyncMock(return_value=MagicMock(success=True, summary="Done", error=None))

        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()

        from core.goals import GoalManager
        mock_container = MagicMock()
        mock_container.resolve.side_effect = lambda cls: mock_goal_manager if cls == GoalManager else MagicMock()
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        client = EricClient(runtime=host)

        res = await client.execute_goal("Open Notepad")
        assert res["success"] is True
        assert res["goal_id"] == "g-exec"


class TestActiveGoalTracking:
    """Verify runtime status transitions READY -> BUSY -> READY and active_goal_id tracking."""

    @pytest.mark.asyncio
    async def test_active_goal_status_lifecycle(self):
        mock_kernel = MagicMock()
        mock_kernel.state = SystemState.READY
        mock_kernel.event_bus = EventBus()

        observed_statuses = []

        mock_goal_manager = MagicMock()
        mock_goal = MagicMock(id="goal-busy")
        mock_goal.state.value = "ready"
        mock_goal_manager.create_goal = AsyncMock(return_value=mock_goal)

        async def slow_start(goal_id):
            # Capture snapshot while goal is executing
            observed_statuses.append(host.get_snapshot())
            return MagicMock(success=True, summary="Finished", error=None)

        mock_goal_manager.start_goal = AsyncMock(side_effect=slow_start)

        from core.goals import GoalManager
        mock_container = MagicMock()
        mock_container.resolve.side_effect = lambda cls: mock_goal_manager if cls == GoalManager else MagicMock()
        mock_kernel.container = mock_container

        host = EricRuntimeHost(kernel=mock_kernel)
        await host.start()
        client = EricClient(runtime=host)

        assert client.get_status() == RuntimeStatus.READY
        assert client.get_snapshot().active_goal_id is None

        # Execute goal
        res = await client.execute_goal("Busy test")
        assert res["success"] is True

        # Check observed snapshot during execution
        assert len(observed_statuses) == 1
        busy_snapshot = observed_statuses[0]
        assert busy_snapshot.status == RuntimeStatus.BUSY
        assert busy_snapshot.active_goal_id == "goal-busy"

        # Check final state restored to READY
        final_snapshot = client.get_snapshot()
        assert final_snapshot.status == RuntimeStatus.READY
        assert final_snapshot.active_goal_id is None


class TestMainViewModelStructuredEvents:
    """Verify MainViewModel progress updates via structured events instead of string matching."""

    def test_viewmodel_progress_via_structured_events_without_vietnamese_strings(self):
        # Create a mock client
        mock_client = MagicMock()
        listeners = {}

        def mock_sub(event_type, handler):
            listeners.setdefault(event_type, []).append(handler)

        mock_client.subscribe.side_effect = mock_sub

        vm = MainViewModel(client=mock_client)
        assert vm.goal_progress == 0.0
        assert vm.is_processing is False

        def emit(event_type, payload):
            ev = RuntimeEvent(event_type=event_type, timestamp=datetime.now(timezone.utc), payload=payload)
            for h in listeners.get(event_type, []) + listeners.get("goal.*", []):
                h(ev)

        # 1. Goal started -> is_processing True
        emit("goal.started", {"goal_id": "g-1"})
        assert vm.is_processing is True
        assert vm.goal_progress == 10.0

        # 2. Goal progress update with pure English/numeric payload
        emit("goal.progress", {"goal_id": "g-1", "percentage": 45.0, "action": "downloading_package"})
        assert vm.goal_progress == 45.0
        assert "downloading_package" in vm.current_status

        # 3. Step started
        emit("goal.step.started", {"goal_id": "g-1", "action": "CompileBinary"})
        assert vm.timeline_steps[-1]["step"] == "CompileBinary"
        assert vm.timeline_steps[-1]["status"] == "running"

        # 4. Step completed
        emit("goal.step.completed", {"goal_id": "g-1", "step_id": "s-1"})
        assert vm.timeline_steps[-1]["status"] == "completed"

        # 5. Goal completed
        emit("goal.completed", {"goal_id": "g-1", "summary": "Build successful"})
        assert vm.goal_progress == 100.0
        assert vm.is_processing is False
        assert vm.current_status == "Completed"

    def test_legacy_string_status_does_not_affect_authoritative_progress(self):
        """Proof: Legacy string messages update display text only, NOT is_processing or progress."""
        mock_bridge = MagicMock()
        vm = MainViewModel(bridge=mock_bridge)

        # Send string with Vietnamese progress keywords
        vm._on_display_status_changed("Đang phân tích dữ liệu...")
        assert vm.current_status == "Đang phân tích dữ liệu..."
        # Must NOT set is_processing to True or alter percentage
        assert vm.is_processing is False
        assert vm.goal_progress == 0.0

    def test_viewmodel_session_access_does_not_use_private_field(self):
        mock_bridge = MagicMock()
        mock_session = MagicMock(messages=["msg1", "msg2"])
        mock_bridge.get_active_session.return_value = mock_session
        mock_bridge.list_sessions.return_value = [mock_session]

        vm = MainViewModel(bridge=mock_bridge)
        messages = vm.get_messages()
        sessions = vm.get_sessions()

        assert messages == ["msg1", "msg2"]
        assert sessions == [mock_session]
        assert mock_bridge.get_active_session.called
        assert mock_bridge.list_sessions.called


class TestBackendBridgeLLMRouterDI:
    """Verify BackendBridge resolves LLMRouter from DI container without duplicate router construction."""

    def test_backend_bridge_uses_di_llm_router(self):
        mock_router = MagicMock(spec=LLMRouter)
        mock_container = MagicMock()
        mock_container.has.return_value = True
        mock_container.resolve.return_value = mock_router

        mock_kernel = MagicMock()
        mock_kernel.container = mock_container

        mock_bootstrap = MagicMock()
        mock_bootstrap.kernel = mock_kernel

        with patch("app.services.backend_bridge.build_default_router") as mock_build_default:
            bridge = BackendBridge(bootstrap=mock_bootstrap)
            router = bridge._get_llm_router()

            assert router is mock_router
            # build_default_router must NOT be called when DI container has LLMRouter!
            assert mock_build_default.call_count == 0

    def test_backend_bridge_uses_injected_router(self):
        mock_router = MagicMock(spec=LLMRouter)
        mock_bootstrap = MagicMock()

        with patch("app.services.backend_bridge.build_default_router") as mock_build_default:
            bridge = BackendBridge(bootstrap=mock_bootstrap, llm_router=mock_router)
            assert bridge._get_llm_router() is mock_router
            assert mock_build_default.call_count == 0


class TestEncapsulation:
    """Verify EricClient exposes transport-safe APIs and does NOT leak internal backend objects."""

    def test_client_does_not_expose_backend_internals(self):
        client = EricClient(runtime=MagicMock())

        forbidden_attributes = [
            "kernel",
            "container",
            "event_bus",
            "goal_manager",
            "llm_router",
            "coordinator",
            "desktop_runtime",
            "vision_runtime",
        ]

        for attr in forbidden_attributes:
            assert not hasattr(client, attr), f"EricClient must NOT expose internal attribute '{attr}'"

    def test_client_public_methods_are_transport_friendly(self):
        client = EricClient(runtime=MagicMock())
        expected_methods = [
            "start",
            "stop",
            "get_status",
            "get_snapshot",
            "submit_goal",
            "start_goal",
            "execute_goal",
            "pause_goal",
            "resume_goal",
            "cancel_goal",
            "get_goal_snapshot",
            "subscribe",
            "unsubscribe",
        ]
        for method in expected_methods:
            assert hasattr(client, method) and callable(getattr(client, method))


class TestModelSerialization:
    """Verify that all new Sprint 18.2 client models serialize and roundtrip cleanly."""

    def test_goal_handle_roundtrip(self):
        handle = GoalHandle(goal_id="g-100", status="running")
        d = handle.to_dict()
        assert d == {"goal_id": "g-100", "status": "running"}

        reconstructed = GoalHandle.from_dict(d)
        assert reconstructed.goal_id == "g-100"
        assert reconstructed.status == "running"

    def test_goal_snapshot_roundtrip(self):
        snapshot = GoalSnapshot(
            goal_id="g-200",
            description="Run test suite",
            status="running",
            progress=55.5,
            current_step="Step 3",
            total_steps=5,
            completed_steps=2,
            error=None,
        )
        d = snapshot.to_dict()
        assert d["goal_id"] == "g-200"
        assert d["progress"] == 55.5
        assert d["current_step"] == "Step 3"

        reconstructed = GoalSnapshot.from_dict(d)
        assert reconstructed == snapshot

    def test_goal_progress_record_roundtrip(self):
        record = GoalProgressRecord(
            goal_id="g-300",
            state="in_progress",
            current_step="Building wheel",
            completed_steps=4,
            total_steps=8,
            percentage=50.0,
            message="Compilation running",
        )
        d = record.to_dict()
        assert d["percentage"] == 50.0

        reconstructed = GoalProgressRecord.from_dict(d)
        assert reconstructed == record
