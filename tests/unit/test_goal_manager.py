"""
Unit Tests for Sprint 14 — Goal Manager & Autonomous Planning (v1.0 Final).
"""

import asyncio
import pytest

from core.events.event_bus import EventBus
from core.goals import (
    AutonomousGoalPlanner,
    CapabilityRequirement,
    DynamicReplanner,
    ExecutionContext,
    GoalArtifact,
    GoalCostEstimator,
    GoalDecomposer,
    GoalManager,
    GoalPolicy,
    GoalPriority,
    GoalState,
    GoalType,
    ProgressTracker,
    RelationType,
    SuccessCriterion,
)
from core.runtime.capability import CapabilityNegotiator
from core.desktop import MockDesktopAdapter
from core.vision import MockVisionAdapter


@pytest.mark.asyncio
async def test_goal_creation_specification_and_criteria():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)

    goal = await manager.create_goal(
        "Download monthly revenue report",
        title="Revenue Download",
        intent="Obtain excel report for July 2026",
        goal_type=GoalType.BROWSER,
    )

    assert goal.id is not None
    assert goal.state == GoalState.READY
    assert goal.spec.title == "Revenue Download"
    assert goal.spec.intent == "Obtain excel report for July 2026"
    assert len(goal.spec.success_criteria) > 0
    assert isinstance(goal.policy, GoalPolicy)


def test_capability_requirement_layers():
    req = CapabilityRequirement(
        required=["mouse"],
        preferred=["desktop"],
        optional=["vision"],
    )
    assert req.required == ["mouse"]
    assert req.preferred == ["desktop"]
    assert req.optional == ["vision"]


def test_cost_estimator():
    estimator = GoalCostEstimator()
    planner = AutonomousGoalPlanner()
    decomposer = GoalDecomposer()

    spec = decomposer.decompose(type("Spec", (), {"description": "Download revenue report", "title": "Report", "intent": "Download", "goal_type": GoalType.BROWSER, "priority": GoalPriority.NORMAL, "timeout_seconds": 300, "success_criteria": []})())
    plan = planner.build_plan(spec)

    cost = estimator.estimate_cost(spec.spec, plan)
    assert cost.estimated_seconds > 0
    assert cost.estimated_tokens > 0
    assert cost.estimated_steps == len(plan.steps)


def test_goal_dag_multi_relations():
    decomposer = GoalDecomposer()
    spec = type("Spec", (), {"description": "Download revenue report", "title": "Report", "intent": "Download", "goal_type": GoalType.BROWSER, "priority": GoalPriority.NORMAL, "timeout_seconds": 300, "success_criteria": []})()
    goal = decomposer.decompose(spec)

    has_optional = False
    for rel in goal.graph.relations:
        if rel.relation_type == RelationType.OPTIONAL:
            has_optional = True
            break
    assert has_optional is True


@pytest.mark.asyncio
async def test_execution_context_snapshot_pause_resume():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    negotiator.register_runtime("desktop", MockDesktopAdapter(event_bus))

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
    goal = await manager.create_goal("Execute desktop task")

    goal.progress.current_step_index = 1
    goal.state = GoalState.RUNNING

    paused = await manager.pause_goal(goal.id)
    assert paused is True
    assert goal.state == GoalState.PAUSED

    resumed_step = manager._context.restore_goal_state(goal)
    assert resumed_step == 1
    assert goal.state == GoalState.RUNNING


@pytest.mark.asyncio
async def test_goal_artifact_generated_on_completion():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    negotiator.register_runtime("desktop", MockDesktopAdapter(event_bus))

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
    goal = await manager.create_goal("Execute desktop goal with artifact generation")

    res = await manager.start_goal(goal.id)
    assert res.success is True

    # Goal Artifact must be populated
    assert goal.artifact is not None
    assert isinstance(goal.artifact, GoalArtifact)
    assert goal.artifact.goal_id == goal.id
    assert len(goal.artifact.logs) > 0
    assert len(goal.artifact.timeline) > 0
    assert goal.artifact.telemetry_snapshot["success"] is True
