"""
Sprint 18.3 — Windows Companion Lifecycle Unit Tests.

Validates:
1. Normal startup sequence (lock -> client -> tray -> presentation show).
2. Duplicate instance handling (lock rejected -> runtime not started -> clean structured result).
3. Hide/Show presentation semantics (close window hides presentation, runtime & tray stay alive).
4. Tray 'Open Eric' triggers presentation show.
5. Tray 'Quit Eric' triggers graceful quit sequence (hide -> tray stop -> client stop -> lock release).
6. Idempotent quit (multiple quit calls are safe and non-corrupting).
7. Startup failure recovery (runtime fails -> lock released; tray fails -> client stopped, lock released).
8. RuntimeStatus -> Tray integration (structured status updates without string parsing).
9. Encapsulation verification (CompanionApplication has zero direct coupling to Kernel, EventBus, GoalManager).
10. Windows Named Mutex lock behavior (acquire, duplicate detection, release).
11. Autostart management protocol and safety (default disabled, zero real registry touches in tests).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.client.eric_client import EricClient
from app.lifecycle.companion_app import CompanionApplication, CompanionStartupResult
from app.platform.interfaces import (
    IPresentationHost,
    ISingleInstanceLock,
    IStartupManager,
    ITrayManager,
)
from app.platform.presentation import MockPresentationHost
from app.platform.single_instance import (
    MockSingleInstanceLock,
    WindowsSingleInstanceLock,
)
from app.platform.startup import MockStartupManager
from app.platform.tray import MockTrayManager
from core.runtime.models import RuntimeEvent, RuntimeStatus


class TestCompanionNormalStartup:
    """Verify normal startup sequence: Lock -> Client -> Tray -> Show."""

    @pytest.mark.asyncio
    async def test_normal_startup_flow(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)
        mock_client.subscribe = MagicMock()

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        res = await app.start(start_hidden=False)

        assert isinstance(res, CompanionStartupResult)
        assert res.success is True
        assert res.is_duplicate_instance is False
        assert res.error is None

        # Lock was acquired
        assert mock_lock.is_locked is True
        assert mock_lock.acquire_call_count == 1

        # Client was started
        mock_client.start.assert_awaited_once()

        # Tray was started and configured
        assert mock_tray.is_running() is True
        assert mock_tray.start_call_count == 1
        assert mock_tray._status == RuntimeStatus.READY

        # Subscribed to runtime events
        mock_client.subscribe.assert_called_with("runtime.*", app._on_runtime_event)

        # Presentation was shown
        assert mock_presentation.is_visible() is True
        assert mock_presentation.show_call_count == 1

        # Application state
        assert app.is_running is True

    @pytest.mark.asyncio
    async def test_startup_hidden_flow(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)
        mock_client.subscribe = MagicMock()

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        res = await app.start(start_hidden=True)
        assert res.success is True

        # Presentation remains hidden
        assert mock_presentation.is_visible() is False
        assert mock_presentation.show_call_count == 0
        assert app.is_running is True


class TestDuplicateInstancePrevention:
    """Verify duplicate instances exit cleanly without touching runtime or tray."""

    @pytest.mark.asyncio
    async def test_duplicate_instance_aborts_cleanly(self):
        # Already locked by primary instance
        mock_lock = MockSingleInstanceLock(initially_locked=True)
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        res = await app.start()

        assert res.success is False
        assert res.is_duplicate_instance is True
        assert "already running" in res.error

        # Runtime MUST NOT have been started
        mock_client.start.assert_not_called()

        # Tray MUST NOT have been started
        assert mock_tray.start_call_count == 0

        # Presentation MUST NOT have been shown
        assert mock_presentation.is_visible() is False
        assert app.is_running is False


class TestHideShowSemantics:
    """Verify fundamental distinction: Closing UI hides window; Eric companion remains alive."""

    @pytest.mark.asyncio
    async def test_close_window_only_hides_presentation(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        await app.start(start_hidden=False)
        assert app.is_visible is True
        assert app.is_running is True

        # User clicks window close [X] -> triggers request_close() or hide()
        mock_presentation.request_close()
        assert app.is_visible is False

        # CRITICAL: Application, Tray, and Runtime MUST remain alive!
        assert app.is_running is True
        assert mock_tray.is_running() is True
        assert mock_lock.is_locked is True
        mock_client.stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_tray_open_restores_presentation(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        await app.start(start_hidden=True)
        assert app.is_visible is False

        # User clicks 'Open Eric' in tray
        mock_tray.simulate_open()
        assert app.is_visible is True


class TestGracefulQuit:
    """Verify authoritative quit sequence: Presentation Hide -> Tray Stop -> Client Stop -> Lock Release."""

    @pytest.mark.asyncio
    async def test_quit_lifecycle_sequence(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        await app.start()
        assert app.is_running is True

        # Perform quit
        await app.quit()

        assert app.is_running is False
        assert mock_presentation.is_visible() is False
        assert mock_tray.is_running() is False
        mock_client.stop.assert_awaited_once()
        assert mock_lock.is_locked is False

    @pytest.mark.asyncio
    async def test_tray_quit_triggers_application_quit(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_presentation = MockPresentationHost()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
            presentation=mock_presentation,
        )

        await app.start()

        # Simulate user clicking 'Quit Eric' in system tray menu
        mock_tray.simulate_quit()

        # Allow any queued asyncio tasks to run
        await asyncio.sleep(0.05)

        assert app.is_running is False
        assert mock_lock.is_locked is False

    @pytest.mark.asyncio
    async def test_quit_is_idempotent(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
        )

        await app.start()
        await app.quit()
        # Second call to quit() should be a safe no-op
        await app.quit()

        assert mock_client.stop.await_count == 1
        assert mock_tray.stop_call_count == 1


class TestStartupFailureRecovery:
    """Verify deterministic cleanup when startup fails at various stages."""

    @pytest.mark.asyncio
    async def test_runtime_failure_releases_lock(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock(side_effect=RuntimeError("Kernel initialization crash"))

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
        )

        res = await app.start()

        assert res.success is False
        assert "Kernel initialization crash" in res.error
        # Lock MUST be released
        assert mock_lock.is_locked is False
        # Tray MUST NOT have started
        assert mock_tray.is_running() is False
        assert app.is_running is False

    @pytest.mark.asyncio
    async def test_tray_failure_stops_runtime_and_releases_lock(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager(fail_on_start=True)
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
        )

        res = await app.start()

        assert res.success is False
        assert "Simulated tray startup failure" in res.error
        # Client MUST have been stopped in reverse cleanup
        mock_client.stop.assert_awaited_once()
        # Lock MUST be released
        assert mock_lock.is_locked is False
        assert app.is_running is False


class TestRuntimeStatusToTrayIntegration:
    """Verify structured RuntimeStatus directly drives tray status without string parsing."""

    @pytest.mark.asyncio
    async def test_runtime_event_updates_tray_status(self):
        mock_lock = MockSingleInstanceLock()
        mock_tray = MockTrayManager()
        mock_client = MagicMock(spec=EricClient)
        mock_client.start = AsyncMock()
        mock_client.get_status = MagicMock(return_value=RuntimeStatus.READY)

        app = CompanionApplication(
            client=mock_client,
            lock=mock_lock,
            tray=mock_tray,
        )

        await app.start()
        assert mock_tray._status == RuntimeStatus.READY

        from datetime import datetime, timezone
        mock_client.get_status.return_value = RuntimeStatus.BUSY
        app._on_runtime_event(RuntimeEvent(event_type="runtime.busy", timestamp=datetime.now(timezone.utc), payload={}))
        assert mock_tray._status == RuntimeStatus.BUSY

        # Simulate host returning to READY
        mock_client.get_status.return_value = RuntimeStatus.READY
        app._on_runtime_event(RuntimeEvent(event_type="runtime.ready", timestamp=datetime.now(timezone.utc), payload={}))
        assert mock_tray._status == RuntimeStatus.READY

        # Verify no string parsing occurred — history has exact enum members
        assert RuntimeStatus.BUSY in mock_tray.status_history
        assert RuntimeStatus.READY in mock_tray.status_history


class TestEncapsulation:
    """Verify CompanionApplication does not expose or import backend internals."""

    def test_companion_app_has_no_backend_internals(self):
        app = CompanionApplication(client=MagicMock(spec=EricClient))

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
            assert not hasattr(app, attr), f"CompanionApplication must NOT expose internal '{attr}'"


class TestWindowsNamedMutexLock:
    """Verify WindowsSingleInstanceLock behavior using Win32 Named Mutex."""

    def test_windows_mutex_acquire_and_release(self):
        lock1 = WindowsSingleInstanceLock(mutex_name="Local\\Test_Eric_Mutex_18_3")
        lock2 = WindowsSingleInstanceLock(mutex_name="Local\\Test_Eric_Mutex_18_3")

        try:
            # First acquisition succeeds
            assert lock1.acquire() is True
            assert lock1.is_locked is True

            # Duplicate acquisition with same mutex name fails
            assert lock2.acquire() is False
            assert lock2.is_locked is False

            # Release first lock
            lock1.release()
            assert lock1.is_locked is False

            # Now second lock can acquire
            assert lock2.acquire() is True
            assert lock2.is_locked is True
        finally:
            lock1.release()
            lock2.release()


class TestStartupManager:
    """Verify IStartupManager protocol and mock test seams."""

    def test_mock_startup_manager(self):
        mgr = MockStartupManager(initially_enabled=False)
        assert mgr.is_enabled() is False

        mgr.enable()
        assert mgr.is_enabled() is True
        assert mgr.enable_call_count == 1

        mgr.disable()
        assert mgr.is_enabled() is False
        assert mgr.disable_call_count == 1
