"""
Goal Recovery Manager.
Handles step failure decisions: Retry, Recover, Skip, Ask User, or Abort.
"""

from typing import Tuple

from core.goals.enums import GoalState, StepPolicy
from core.goals.models import ExecutionStep, Goal


class GoalRecoveryManager:
    """
    Decides recovery behavior when an ExecutionStep fails.
    """

    def handle_step_failure(self, goal: Goal, step: ExecutionStep, error_msg: str) -> Tuple[GoalState, StepPolicy]:
        """
        Determines new GoalState and StepPolicy when a step fails.
        """
        goal.progress.recovery_count += 1
        goal.progress.planner_confidence *= 0.85

        if step.policy == StepPolicy.SKIP or step.policy == StepPolicy.IGNORE if hasattr(StepPolicy, "IGNORE") else False:
            return GoalState.RUNNING, StepPolicy.SKIP

        if step.policy == StepPolicy.ABORT:
            goal.state = GoalState.FAILED
            return GoalState.FAILED, StepPolicy.ABORT

        if step.policy == StepPolicy.ASK_USER:
            goal.state = GoalState.WAITING
            return GoalState.WAITING, StepPolicy.ASK_USER

        # Default recovery attempt
        if goal.progress.recovery_count <= 3:
            goal.state = GoalState.RECOVERING
            return GoalState.RECOVERING, StepPolicy.RECOVER
        else:
            goal.state = GoalState.FAILED
            return GoalState.FAILED, StepPolicy.ABORT
