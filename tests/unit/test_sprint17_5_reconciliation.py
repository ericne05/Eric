"""
Unit tests for Sprint 17.5 Architectural Reconciliation & Hardening.
Verifies security, boundary decoupling, action delegation, and bootstrap integration.
"""

import sys
import pytest
from pathlib import Path

from core.desktop import WindowsDesktopAdapter
from core.events.event_bus import EventBus
from core.goals.enums import GoalState
from core.goals.models import Goal
from core.cognition.models import SharedCognitiveContext
from core.cognition.coordinator import CognitiveCoordinator
from core.runtime.capability import CapabilityNegotiator


class TestSprint175Security:
    """Verifies security fixes and PyInstaller spec compliance."""

    def test_env_not_in_eric_spec_datas(self):
        spec_path = Path("eric.spec")
        assert spec_path.exists(), "eric.spec must exist"
        spec_content = spec_path.read_text(encoding="utf-8")

        assert "('.env', '.')" not in spec_content, "Critical vulnerability: .env must NOT be packaged in datas!"
        assert "('configs', 'configs')" in spec_content, "configs directory should be packaged"


class TestWindowsDesktopAdapterDelegation:
    """Verifies WindowsDesktopAdapter.execute action delegation."""

    @pytest.mark.asyncio
    async def test_execute_delegates_actions(self):
        bus = EventBus()
        adapter = WindowsDesktopAdapter(event_bus=bus, sandbox=True)

        plan = [
            {"action": "click", "x": 100, "y": 200},
            {"action": "type_text", "text": "hello"},
            {"action": "hotkey", "keys": ["ctrl", "c"]},
            {"action": "launch", "target": "notepad"},
        ]

        result = await adapter.execute(plan)

        assert result["success"] is True
        assert result["actions_executed"] == 4
        assert len(result["results"]) == 4


from core.goals.models import Goal, GoalSpecification

class TestCognitiveCoordinatorGoalState:
    """Verifies CognitiveCoordinator respects GoalState pause and cancellation."""

    @pytest.mark.asyncio
    async def test_coordinator_respects_paused_state(self):
        negotiator = CapabilityNegotiator()
        coordinator = CognitiveCoordinator(negotiator=negotiator)

        goal = Goal(id="g-1", spec=GoalSpecification(title="Test Goal", intent="test"), state=GoalState.PAUSED)
        ctx = SharedCognitiveContext(goal=goal)

        res = await coordinator.run_cognition_loop(ctx)

        assert res.success is False
        assert "paused" in res.error.lower()

    @pytest.mark.asyncio
    async def test_coordinator_respects_cancelled_state(self):
        negotiator = CapabilityNegotiator()
        coordinator = CognitiveCoordinator(negotiator=negotiator)

        goal = Goal(id="g-2", spec=GoalSpecification(title="Test Goal 2", intent="test"), state=GoalState.CANCELLED)
        ctx = SharedCognitiveContext(goal=goal)

        res = await coordinator.run_cognition_loop(ctx)

        assert res.success is False
        assert "cancelled" in res.error.lower()


class TestAppBootstrapIntegration:
    """Verifies AppBootstrap initializes Kernel and uses Kernel's EventBus."""

    @pytest.mark.asyncio
    async def test_app_bootstrap_kernel_integration(self):
        from app.bootstrap.app_bootstrap import AppBootstrap

        bootstrap = AppBootstrap()
        res = await bootstrap.initialize()

        assert res["status"] == "ready"
        assert bootstrap.kernel is not None
        assert bootstrap.event_bus is not None
        assert bootstrap.event_bus == bootstrap.kernel.event_bus
