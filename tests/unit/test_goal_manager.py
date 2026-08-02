"""
Unit Tests for Sprint 14 — Goal Manager & Autonomous Planning.
"""

import asyncio
import pytest

from core.events.event_bus import EventBus
from core.goals import (
    AutonomousGoalPlanner,
    DynamicReplanner,
    ExecutionContext,
    GoalCostEstimator,
    GoalDecomposer,
    GoalManager,
    GoalPriority,
    GoalState,
    GoalType,
    ProgressTracker,
    RelationType,
)
from core.runtime.capability import CapabilityNegotiator
from core.desktop import MockDesktopAdapter


@pytest.mark.asyncio
async def test_goal_creation_and_decomposition():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)

    goal = await manager.create_goal("Download monthly revenue report", goal_type=GoalType.BROWSER)

    assert goal.id is not None
    assert goal.state == GoalState.READY
    assert goal.spec.description == "Download monthly revenue report"
    assert len(goal.graph.subgoals) >= 4
    assert len(goal.plan.steps) >= 4


def test_cost_estimator():
    estimator = GoalCostEstimator()
    planner = AutonomousGoalPlanner()
    decomposer = GoalDecomposer()

    spec = decomposer.decompose(type("Spec", (), {"description": "Download revenue report", "goal_type": GoalType.BROWSER, "priority": GoalPriority.NORMAL, "timeout_seconds": 300})())
    plan = planner.build_plan(spec)

    cost = estimator.estimate_cost(spec.spec, plan)
    assert cost.estimated_seconds > 0
    assert cost.estimated_tokens > 0
    assert cost.estimated_steps == len(plan.steps)


def test_goal_dag_multi_relations():
    decomposer = GoalDecomposer()
    spec = type("Spec", (), {"description": "Download revenue report", "goal_type": GoalType.BROWSER, "priority": GoalPriority.NORMAL, "timeout_seconds": 300})()
    goal = decomposer.decompose(spec)

    has_optional = False
    for rel in goal.graph.relations:
        if rel.relation_type == RelationType.OPTIONAL:
            has_optional = True
            break
    assert has_optional is True


def test_progress_tracker():
    event_bus = EventBus()
    tracker = ProgressTracker(event_bus)

    progress = tracker.update_progress("g1", step_index=2, total_steps=4, current_runtime="desktop")
    assert progress.percentage == 50.0
    assert progress.current_runtime == "desktop"


@pytest.mark.asyncio
async def test_execution_context_snapshot_pause_resume():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    negotiator.register_runtime("desktop", MockDesktopAdapter(event_bus))

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
    goal = await manager.create_goal("Execute desktop task")

    # Set step index
    goal.progress.current_step_index = 1
    goal.state = GoalState.RUNNING

    # Pause goal
    paused = await manager.pause_goal(goal.id)
    assert paused is True
    assert goal.state == GoalState.PAUSED

    # Resume step restoration
    resumed_step = manager._context.restore_goal_state(goal)
    assert resumed_step == 1
    assert goal.state == GoalState.RUNNING


def test_dynamic_replanning():
    replanner = DynamicReplanner()
    planner = AutonomousGoalPlanner()
    decomposer = GoalDecomposer()

    goal = decomposer.decompose(type("Spec", (), {"description": "Download revenue report", "goal_type": GoalType.BROWSER, "priority": GoalPriority.NORMAL, "timeout_seconds": 300})())
    goal.plan = planner.build_plan(goal)

    failed_step = goal.plan.steps[1]
    failed_step.status = "failed"

    new_plan = replanner.replan(goal, failed_step, "Network timeout")
    assert new_plan.version == 2
    assert any("recover" in s.action_name for s in new_plan.steps)
