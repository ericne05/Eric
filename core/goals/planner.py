"""
Autonomous Goal Planner & Dynamic Replanner.
"""

from typing import List

from core.goals.decomposition import GoalDecomposer
from core.goals.interfaces import IGoalPlanner, IReplanner
from core.goals.models import (
    ExecutionPlan,
    ExecutionStep,
    Goal,
    GoalSpecification,
    SubGoal,
)


class DynamicReplanner(IReplanner):
    """
    Independent Replanner Strategy.
    Generates a new ExecutionPlan when step execution fails or environment changes.
    """

    def replan(self, goal: Goal, failed_step: ExecutionStep, error_msg: str) -> ExecutionPlan:
        new_plan = ExecutionPlan(
            goal_id=goal.id,
            version=goal.plan.version + 1,
        )

        # Copy completed steps
        for step in goal.plan.steps:
            if step.status == "completed":
                new_plan.steps.append(step)

        # Insert recovery / fallback step for failed step
        recovery_step = ExecutionStep(
            subgoal_id=failed_step.subgoal_id,
            action_name=f"recover_{failed_step.action_name}",
            capability_required=failed_step.capability_required or "mouse",
            arguments={"reason": error_msg, "original_args": failed_step.arguments},
            estimated_duration_sec=2.0,
        )
        new_plan.steps.append(recovery_step)

        # Re-add pending steps
        found_failed = False
        for step in goal.plan.steps:
            if step.id == failed_step.id:
                found_failed = True
                continue
            if found_failed and step.status == "pending":
                new_plan.steps.append(step)

        return new_plan


class AutonomousGoalPlanner(IGoalPlanner):
    """
    Autonomous Goal Planner that decomposes specs into SubGoal DAGs
    and builds capability-mapped ExecutionPlans.
    """

    def __init__(self, decomposer: GoalDecomposer = None):
        self._decomposer = decomposer or GoalDecomposer()

    def decompose(self, spec: GoalSpecification) -> Goal:
        return self._decomposer.decompose(spec)

    def build_plan(self, goal: Goal) -> ExecutionPlan:
        plan = ExecutionPlan(goal_id=goal.id)

        for sg_id, subgoal in goal.graph.subgoals.items():
            step = ExecutionStep(
                subgoal_id=sg_id,
                action_name=subgoal.title.lower().replace(" ", "_"),
                capability_required=subgoal.required_capability,
                arguments={"description": subgoal.description},
                estimated_duration_sec=1.5,
            )
            plan.steps.append(step)

        return plan
