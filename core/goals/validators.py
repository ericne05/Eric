"""
Goal & Step Validators.
"""

from typing import Any

from core.goals.interfaces import IGoalValidator
from core.goals.models import ExecutionStep, Goal, GoalState


class GoalValidator(IGoalValidator):
    """
    Validates step results and final Goal completion criteria.
    """

    def validate_step(self, step: ExecutionStep, result_data: Any) -> bool:
        if result_data is None:
            return False
        if isinstance(result_data, dict):
            return result_data.get("success", True)
        return True

    def validate_completion(self, goal: Goal) -> bool:
        if not goal.plan.steps:
            return False
        
        # Check all required steps
        for step in goal.plan.steps:
            if step.status == "failed":
                # Find matching subgoal
                subgoal = goal.graph.subgoals.get(step.subgoal_id)
                if subgoal:
                    prereqs = goal.graph.get_prerequisites(subgoal.id)
                    # If any required prerequisite failed, goal is not complete
                    for p_sub, r_type in prereqs:
                        if r_type.value == "required" and p_sub.status == "failed":
                            return False
                else:
                    return False
        return True
