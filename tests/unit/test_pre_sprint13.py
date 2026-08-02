"""
Unit Tests for Pre-Sprint 13 Enhancements:
  1. Telemetry Dashboard
  2. Capability Negotiation
  3. Unified Runtime API (IRuntime)
"""

import asyncio
import datetime
import pytest

from core.browser.enums import WorkflowState
from core.events.event import Event
from core.events.event_bus import EventBus
from core.runtime.capability import CapabilityNegotiator, CapabilityRegistry
from core.runtime.interfaces import IRuntime, IRuntimeCapability
from core.telemetry.dashboard import TelemetryDashboard


# ── Mock Runtime implementing IRuntime ────────────────────────────────────

class MockCapability(CapabilityRegistry):
    pass


class FakeDesktopRuntime(IRuntime):
    """A fake Desktop Runtime implementing the Unified IRuntime interface."""

    def __init__(self):
        self._caps = CapabilityRegistry({
            "mouse": True,
            "keyboard": True,
            "window": True,
            "screenshot": True,
            "clipboard": True,
            "ocr": False,
            "voice": False,
        })

    async def start(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def observe(self):
        return {"focused_window": "Notepad", "resolution": (1920, 1080)}

    async def plan(self, goal: str, observation):
        return [{"action": "click", "x": 100, "y": 200}]

    async def execute(self, plan):
        return {"success": True, "actions_executed": len(plan)}

    async def recover(self, error: Exception, context):
        return WorkflowState.RECOVERING

    def get_runtime_capabilities(self) -> IRuntimeCapability:
        return self._caps

    def get_health(self):
        return {"state": "healthy", "mouse_ok": True}


class FakeBrowserRuntime(IRuntime):
    """A fake Browser Runtime implementing the Unified IRuntime interface."""

    def __init__(self):
        self._caps = CapabilityRegistry({
            "navigation": True,
            "dom_interaction": True,
            "screenshot": True,
            "download": True,
            "mouse": False,
            "keyboard": False,
        })

    async def start(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def observe(self):
        return {"url": "https://example.com", "title": "Example"}

    async def plan(self, goal: str, observation):
        return [{"action": "goto", "url": "https://google.com"}]

    async def execute(self, plan):
        return {"success": True}

    async def recover(self, error: Exception, context):
        return WorkflowState.FAILED

    def get_runtime_capabilities(self) -> IRuntimeCapability:
        return self._caps

    def get_health(self):
        return {"state": "healthy"}


# ── Tests ─────────────────────────────────────────────────────────────────

class TestUnifiedRuntimeAPI:
    """Verify the IRuntime lifecycle: observe → plan → execute → recover."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        runtime = FakeDesktopRuntime()
        await runtime.start()

        obs = await runtime.observe()
        assert obs["focused_window"] == "Notepad"

        plan = await runtime.plan("Open file", obs)
        assert len(plan) == 1

        result = await runtime.execute(plan)
        assert result["success"] is True

        recovery_state = await runtime.recover(RuntimeError("test"), {})
        assert recovery_state == WorkflowState.RECOVERING

        await runtime.shutdown()

    def test_health_check(self):
        runtime = FakeDesktopRuntime()
        health = runtime.get_health()
        assert health["state"] == "healthy"
        assert health["mouse_ok"] is True


class TestCapabilityNegotiation:
    """Verify Planner can query and negotiate capabilities across Runtimes."""

    def test_query_single_runtime(self):
        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("desktop", FakeDesktopRuntime())

        caps = negotiator.query_runtime("desktop")
        assert "mouse" in caps
        assert "keyboard" in caps
        assert "ocr" not in caps  # ocr is False

    def test_find_runtimes_supporting(self):
        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("desktop", FakeDesktopRuntime())
        negotiator.register_runtime("browser", FakeBrowserRuntime())

        # Both support screenshot
        screenshot_runtimes = negotiator.find_runtimes_supporting("screenshot")
        assert "desktop" in screenshot_runtimes
        assert "browser" in screenshot_runtimes

        # Only desktop supports mouse
        mouse_runtimes = negotiator.find_runtimes_supporting("mouse")
        assert "desktop" in mouse_runtimes
        assert "browser" not in mouse_runtimes

        # Only browser supports navigation
        nav_runtimes = negotiator.find_runtimes_supporting("navigation")
        assert "browser" in nav_runtimes
        assert "desktop" not in nav_runtimes

    def test_get_all_capabilities(self):
        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("desktop", FakeDesktopRuntime())
        negotiator.register_runtime("browser", FakeBrowserRuntime())

        all_caps = negotiator.get_all_capabilities()
        assert "desktop" in all_caps
        assert "browser" in all_caps
        assert "mouse" in all_caps["desktop"]
        assert "navigation" in all_caps["browser"]

    def test_unregister_runtime(self):
        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("desktop", FakeDesktopRuntime())
        assert "desktop" in negotiator.runtime_names

        negotiator.unregister_runtime("desktop")
        assert "desktop" not in negotiator.runtime_names


class TestCapabilityRegistry:
    def test_supports(self):
        reg = CapabilityRegistry({"mouse": True, "ocr": False})
        assert reg.supports("mouse") is True
        assert reg.supports("ocr") is False
        assert reg.supports("unknown") is False

    def test_get_capability_list(self):
        reg = CapabilityRegistry({"mouse": True, "keyboard": True, "ocr": False})
        caps = reg.get_capability_list()
        assert "mouse" in caps
        assert "keyboard" in caps
        assert "ocr" not in caps

    def test_set_capability(self):
        reg = CapabilityRegistry()
        reg.set_capability("vision", True)
        assert reg.supports("vision") is True


class TestTelemetryDashboard:
    """Verify Dashboard collects metrics passively from EventBus."""

    @pytest.mark.asyncio
    async def test_snapshot_after_actions(self):
        event_bus = EventBus()
        dashboard = TelemetryDashboard(event_bus)

        # Simulate 3 successful actions and 1 failed action
        await event_bus.publish(Event(name="desktop.action.started", source="desktop.ui", payload={"action": "click"}))
        await event_bus.publish(Event(name="desktop.action.completed", source="desktop.ui", payload={"action": "click"}))

        await event_bus.publish(Event(name="desktop.action.started", source="desktop.ui", payload={"action": "type"}))
        await event_bus.publish(Event(name="desktop.action.completed", source="desktop.ui", payload={"action": "type"}))

        await event_bus.publish(Event(name="desktop.action.started", source="desktop.ui", payload={"action": "drag"}))
        await event_bus.publish(Event(name="desktop.action.completed", source="desktop.ui", payload={"action": "drag"}))

        await event_bus.publish(Event(name="desktop.action.started", source="desktop.ui", payload={"action": "hotkey"}))
        await event_bus.publish(Event(name="desktop.action.failed", source="desktop.ui", payload={"action": "hotkey", "error": "Key not found"}))

        snap = dashboard.snapshot()
        assert snap.total_actions == 4
        assert snap.successful_actions == 3
        assert snap.failed_actions == 1
        assert snap.success_rate == 0.75
        assert snap.recovery_count == 1
        assert snap.queue_length == 0  # All started actions finished

    @pytest.mark.asyncio
    async def test_runtime_health_tracking(self):
        event_bus = EventBus()
        dashboard = TelemetryDashboard(event_bus)

        await event_bus.publish(Event(
            name="desktop.state.changed",
            source="windows_desktop",
            payload={"state": "ready"},
        ))

        snap = dashboard.snapshot()
        assert snap.runtime_health["windows_desktop"] == "ready"

    def test_manual_confidence_update(self):
        event_bus = EventBus()
        dashboard = TelemetryDashboard(event_bus)

        dashboard.update_planner_confidence(0.72)
        snap = dashboard.snapshot()
        assert snap.planner_confidence == 0.72

    @pytest.mark.asyncio
    async def test_emergency_stop_increments_recovery(self):
        event_bus = EventBus()
        dashboard = TelemetryDashboard(event_bus)

        await event_bus.publish(Event(
            name="desktop.emergency_stop",
            source="emergency_manager",
            payload={"reason": "Failsafe triggered"},
        ))

        snap = dashboard.snapshot()
        assert snap.recovery_count == 1

    def test_reset(self):
        event_bus = EventBus()
        dashboard = TelemetryDashboard(event_bus)
        dashboard.update_planner_confidence(0.5)
        dashboard.reset()

        snap = dashboard.snapshot()
        assert snap.total_actions == 0
        assert snap.planner_confidence == 1.0
        assert snap.recovery_count == 0
