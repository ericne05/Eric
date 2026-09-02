"""
Integration Test — Sprint 16: Cognitive Coordination Pipeline.
Tests End-to-End Cognitive Loop:
Goal -> CognitiveCoordinator -> KnowledgeAgent -> PlanningAgent -> ExecutionAgent -> RecoveryAgent -> Telemetry -> Goal Completed.
"""

import asyncio
import pytest

from core.cognition import CognitiveCoordinator, SharedCognitiveContext
from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.goals import Goal, GoalSpecification, GoalState, GoalType
from core.runtime.capability import CapabilityNegotiator
from core.telemetry.dashboard import TelemetryDashboard
from core.vision import MockVisionAdapter


@pytest.mark.asyncio
async def test_full_cognitive_coordination_pipeline():
    event_bus = EventBus()
    dashboard = TelemetryDashboard(event_bus)

    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    negotiator.register_runtime("desktop", desktop)
    negotiator.register_runtime("vision", vision)

    # Initialize CognitiveCoordinator
    coordinator = CognitiveCoordinator(negotiator=negotiator)

    # Create Goal & SharedCognitiveContext
    spec = GoalSpecification(
        title="Full Cognitive Pipeline Test",
        intent="Download report and verify visually",
        goal_type=GoalType.BROWSER,
    )
    goal = Goal(spec=spec)
    ctx = SharedCognitiveContext(goal=goal)

    # Run Cognition Loop
    res = await coordinator.run_cognition_loop(ctx)

    assert res.success is True
    assert ctx.goal.state.value in ("completed", "ready")
    assert len(ctx.history) >= 2

    await desktop.stop()
    await vision.shutdown()
