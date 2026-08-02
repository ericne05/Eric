"""
Goal Cost & Budget Estimator.
Calculates estimated seconds, tokens, and steps BEFORE execution starts.
"""

from core.goals.interfaces import ICostEstimator
from core.goals.models import ExecutionPlan, GoalCostEstimate, GoalSpecification


class GoalCostEstimator(ICostEstimator):
    """
    Estimates pre-execution cost (tokens, time, steps, confidence).
    """

    def estimate_cost(self, spec: GoalSpecification, plan: ExecutionPlan) -> GoalCostEstimate:
        total_steps = len(plan.steps)
        estimated_sec = sum(step.estimated_duration_sec for step in plan.steps)
        if estimated_sec == 0:
            estimated_sec = float(total_steps * 2)

        # Estimate LLM tokens (~150 tokens per step + 500 base prompt)
        estimated_tokens = 500 + (total_steps * 150)
        
        # Estimate confidence (decays slightly with step count)
        confidence = max(0.5, 1.0 - (total_steps * 0.03))

        return GoalCostEstimate(
            estimated_seconds=round(estimated_sec, 2),
            estimated_tokens=estimated_tokens,
            estimated_steps=total_steps,
            estimated_confidence=round(confidence, 2),
        )
