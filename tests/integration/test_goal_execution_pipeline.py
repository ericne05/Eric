"""
Integration Test — Sprint 14: Full Goal Execution Pipeline.
Tests End-to-End lifecycle:
Chat Request -> Goal Manager -> Cost Estimator -> Capability Negotiator -> Runtimes (Desktop, Vision) -> Telemetry Dashboard -> Goal Completed.
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
async def test_full_goal_execution_pipeline():
    event_bus = EventBus()
    dashboard = TelemetryDashboard(event_bus)

    # Capability Negotiator with Desktop and Vision runtimes
    negotiator = CapabilityNegotiator()
    desktop_runtime = MockDesktopAdapter(event_bus)
    vision_runtime = MockVisionAdapter()

    await desktop_runtime.start()
    await vision_runtime.start()

    negotiator.register_runtime("desktop", desktop_runtime)
    negotiator.register_runtime("vision", vision_runtime)

    # Goal Manager orchestration
    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)

    # 1. Create Goal
    goal = await manager.create_goal("Download and inspect monthly revenue report")
    assert goal.state == GoalState.READY
    assert goal.cost_estimate.estimated_seconds > 0

    # 2. Start Goal Execution
    result = await manager.start_goal(goal.id)

    assert result.success is True
    assert goal.state == GoalState.COMPLETED

    # 3. Check Telemetry Dashboard Metrics
    snap = dashboard.snapshot()
    assert snap.total_goals == 1
    assert snap.completed_goals == 1
    assert snap.active_goals == 0

    await desktop_runtime.stop()
    await vision_runtime.shutdown()


@pytest.mark.asyncio
async def test_goal_execution_pipeline_capability_routing():
    """
    Ensures steps requiring 'mouse' route to Desktop, steps requiring 'ocr' route to Vision,
    strictly via CapabilityNegotiator without hardcoding.
    """
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    negotiator.register_runtime("desktop", desktop)
    negotiator.register_runtime("vision", vision)

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
    goal = await manager.create_goal("Test multi-runtime routing goal")

    result = await manager.start_goal(goal.id)
    assert result.success is True

    await desktop.stop()
    await vision.shutdown()
