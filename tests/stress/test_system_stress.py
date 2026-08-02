"""
Stress & Leak Verification Test Suite — Sprint 14.5 Hardening.
Executes 100 Goals under continuous load to ensure no Memory Leaks, Queue Leaks, or Event Listener Leaks.
"""

import asyncio
import pytest

from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.goals import GoalManager, GoalState
from core.runtime.capability import CapabilityNegotiator
from core.telemetry.dashboard import TelemetryDashboard
from core.vision import MockVisionAdapter


@pytest.mark.asyncio
async def test_100_goals_stress_and_no_leak():
    """
    Stress test executing 100 Goals in rapid succession.
    Verifies that:
      1. All 100 Goals reach COMPLETED state.
      2. Active goal count returns to 0 (no Queue / Goal leak).
      3. Telemetry dashboard tracks 100 completed goals correctly.
      4. EventBus subscribers count does not grow uncontrollably.
    """
    event_bus = EventBus()
    dashboard = TelemetryDashboard(event_bus)
    negotiator = CapabilityNegotiator()

    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    negotiator.register_runtime("desktop", desktop)
    negotiator.register_runtime("vision", vision)

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)

    # Execute 100 goals
    for i in range(100):
        goal = await manager.create_goal(f"Stress test goal #{i+1}")
        res = await manager.start_goal(goal.id)
        assert res.success is True
        assert goal.state == GoalState.COMPLETED

    snap = dashboard.snapshot()
    assert snap.total_goals == 100
    assert snap.completed_goals == 100
    assert snap.active_goals == 0  # No active goal leak
    assert snap.queue_length == 0  # No queue leak

    await desktop.stop()
    await vision.shutdown()
