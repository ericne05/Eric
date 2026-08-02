"""
Goal Manager Implementation (Sprint 14 Product-Grade).
"""

import asyncio, time
from typing import Dict, Optional

from core.events.event import Event
from core.events.event_bus import EventBus
from core.goals.estimator import GoalCostEstimator
from core.goals.enums import GoalPriority, GoalState, GoalType, StepPolicy
from core.goals.interfaces import IGoalManager
from core.goals.managers.execution_context import ExecutionContext
from core.goals.managers.progress_tracker import ProgressTracker
from core.goals.managers.recovery import GoalRecoveryManager
from core.goals.models import (
    ExecutionPlan,
    Goal,
    GoalProgress,
    GoalResult,
    GoalSpecification,
)
from core.goals.orchestrator import GoalOrchestrator
from core.goals.planner import AutonomousGoalPlanner, DynamicReplanner
from core.goals.validators import GoalValidator
from core.runtime.capability import CapabilityNegotiator


class GoalManager(IGoalManager):
    """
    Highest-level orchestration controller.
    Manages Goal lifecycle and delegates execution to GoalOrchestrator & CapabilityNegotiator.
    NEVER executes low-level actions directly.
    """

    def __init__(self, negotiator: CapabilityNegotiator, event_bus: Optional[EventBus] = None):
        self._negotiator = negotiator
        self._event_bus = event_bus
        self._planner = AutonomousGoalPlanner()
        self._replanner = DynamicReplanner()
        self._estimator = GoalCostEstimator()
        self._validator = GoalValidator()
        self._orchestrator = GoalOrchestrator(negotiator)
        self._progress_tracker = ProgressTracker(event_bus)
        self._context = ExecutionContext()
        self._recovery_manager = GoalRecoveryManager()

        self._goals: Dict[str, Goal] = {}

    async def _emit(self, name: str, payload: dict):
        if self._event_bus:
            await self._event_bus.publish(
                Event(name=name, source="goal_manager", payload=payload)
            )

    async def create_goal(self, description: str, **kwargs) -> Goal:
        spec = GoalSpecification(
            description=description,
            goal_type=kwargs.get("goal_type", GoalType.MIXED),
            priority=kwargs.get("priority", GoalPriority.NORMAL),
            timeout_seconds=kwargs.get("timeout_seconds", 300),
        )

        goal = self._planner.decompose(spec)
        goal.plan = self._planner.build_plan(goal)
        goal.cost_estimate = self._estimator.estimate_cost(spec, goal.plan)
        goal.state = GoalState.READY

        self._goals[goal.id] = goal
        await self._emit("goal.created", {"goal_id": goal.id, "description": description, "cost": goal.cost_estimate})
        return goal

    async def start_goal(self, goal_id: str) -> GoalResult:
        goal = self._goals.get(goal_id)
        if not goal:
            return GoalResult(success=False, goal_id=goal_id, error="Goal not found")

        goal.state = GoalState.RUNNING
        await self._emit("goal.started", {"goal_id": goal.id})

        start_time = time.time()
        total_steps = len(goal.plan.steps)
        step_idx = goal.progress.current_step_index

        while step_idx < total_steps:
            if goal.state == GoalState.PAUSED:
                self._context.capture_snapshot(goal, step_idx)
                return GoalResult(success=False, goal_id=goal_id, summary="Goal paused")

            if goal.state == GoalState.CANCELLED:
                return GoalResult(success=False, goal_id=goal_id, summary="Goal cancelled")

            step = goal.plan.steps[step_idx]
            step.status = "running"
            await self._emit("goal.step.started", {"goal_id": goal.id, "step_id": step.id, "action": step.action_name})

            # Execute via GoalOrchestrator (which routes via CapabilityNegotiator)
            exec_res = await self._orchestrator.execute_step(step)
            runtime_used = exec_res.get("runtime_used", "none")

            if exec_res.get("success"):
                step.status = "completed"
                await self._emit("goal.step.completed", {"goal_id": goal.id, "step_id": step.id, "runtime_used": runtime_used})
            else:
                error_msg = exec_res.get("error", "Unknown step failure")
                new_state, policy = self._recovery_manager.handle_step_failure(goal, step, error_msg)

                if policy == StepPolicy.RECOVER:
                    goal.plan = self._replanner.replan(goal, step, error_msg)
                    total_steps = len(goal.plan.steps)
                    await self._emit("goal.recovered", {"goal_id": goal.id, "new_version": goal.plan.version})
                    goal.state = GoalState.RUNNING
                elif policy == StepPolicy.ABORT:
                    goal.state = GoalState.FAILED
                    await self._emit("goal.failed", {"goal_id": goal.id, "error": error_msg})
                    return GoalResult(success=False, goal_id=goal_id, error=error_msg)

            step_idx += 1
            self._progress_tracker.update_progress(goal.id, step_idx, total_steps, runtime_used)

        is_valid = self._validator.validate_completion(goal)
        elapsed = time.time() - start_time

        if is_valid or goal.state == GoalState.RUNNING:
            goal.state = GoalState.COMPLETED
            res = GoalResult(success=True, goal_id=goal.id, summary=f"Completed in {elapsed:.2f}s")
            goal.result = res
            await self._emit("goal.completed", {"goal_id": goal.id, "elapsed": elapsed})
            return res
        else:
            goal.state = GoalState.FAILED
            res = GoalResult(success=False, goal_id=goal.id, error="Completion validation failed")
            goal.result = res
            await self._emit("goal.failed", {"goal_id": goal.id, "error": "Validation failed"})
            return res

    async def pause_goal(self, goal_id: str) -> bool:
        goal = self._goals.get(goal_id)
        if not goal or goal.state != GoalState.RUNNING:
            return False

        goal.state = GoalState.PAUSED
        self._context.capture_snapshot(goal, goal.progress.current_step_index)
        await self._emit("goal.paused", {"goal_id": goal_id})
        return True

    async def resume_goal(self, goal_id: str) -> GoalResult:
        goal = self._goals.get(goal_id)
        if not goal or goal.state != GoalState.PAUSED:
            return GoalResult(success=False, goal_id=goal_id, error="Goal not paused")

        resumed_step = self._context.restore_goal_state(goal)
        await self._emit("goal.resumed", {"goal_id": goal_id, "resumed_step": resumed_step})
        return await self.start_goal(goal_id)

    async def cancel_goal(self, goal_id: str) -> bool:
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal.state = GoalState.CANCELLED
        await self._emit("goal.cancelled", {"goal_id": goal_id})
        return True

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)
