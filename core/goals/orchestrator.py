"""
Goal Orchestrator.
Dispatches ExecutionSteps to Runtimes using ONLY the CapabilityNegotiator.
"""

from typing import Any, Dict, Optional

from core.goals.models import ExecutionStep
from core.runtime.capability import CapabilityNegotiator


class GoalOrchestrator:
    """
    Goal Execution Dispatcher.
    Enforces the mandatory constraint: CapabilityNegotiator is the ONLY pathway to resolve Runtimes.
    Uses CapabilityRequirement (required -> preferred -> optional) for graceful runtime fallback.
    """

    def __init__(self, negotiator: CapabilityNegotiator, approval_manager: Optional[Any] = None):
        self._negotiator = negotiator
        self._approval_manager = approval_manager

    async def execute_step(self, step: ExecutionStep) -> Dict[str, Any]:
        # Human-in-the-Loop Approval Gate (Sprint 18.5)
        if self._approval_manager:
            from core.approval.enums import ApprovalStatus
            metadata = {
                "step_id": getattr(step, "id", None),
                "subgoal_id": getattr(step, "subgoal_id", None),
                "capability_requirement": getattr(step, "capability_requirement", None),
                "policy": getattr(step, "policy", None),
            }
            eval_res = self._approval_manager.evaluate_action(
                action_name=step.action_name,
                parameters=step.arguments,
                metadata=metadata,
            )
            if eval_res.requires_approval:
                decision = await self._approval_manager.request_and_wait(
                    action_name=step.action_name,
                    description=f"Execute step '{step.action_name}'",
                    reason=eval_res.reason or f"Action '{step.action_name}' requires user approval.",
                    risk_level=eval_res.risk_level,
                    parameters=step.arguments,
                )
                if decision != ApprovalStatus.APPROVED:
                    return {
                        "success": False,
                        "error": f"Step '{step.action_name}' was {decision.value} by user approval.",
                        "runtime_used": "none",
                        "denied": True,
                    }

        req = step.capability_requirement

        # Extract capabilities to try in sequence: required -> preferred -> optional
        caps_to_try = []
        if req:
            caps_to_try.extend(req.required)
            caps_to_try.extend(req.preferred)
            caps_to_try.extend(req.optional)

        if not caps_to_try:
            caps_to_try = ["mouse"]

        matching_runtimes = []
        target_cap = "mouse"

        for cap in caps_to_try:
            runtimes = self._negotiator.find_runtimes_supporting(cap)
            if runtimes:
                matching_runtimes = runtimes
                target_cap = cap
                break

        if not matching_runtimes:
            # Global fallback
            matching_runtimes = self._negotiator.find_runtimes_supporting("screenshot")

        if not matching_runtimes:
            return {
                "success": False,
                "error": f"No registered Runtime supports required capabilities '{caps_to_try}'",
                "runtime_used": "none",
            }

        selected_runtime_name = matching_runtimes[0]
        runtime_instance = self._negotiator._runtimes.get(selected_runtime_name)

        if not runtime_instance:
            return {"success": False, "error": f"Runtime '{selected_runtime_name}' not accessible", "runtime_used": selected_runtime_name}

        try:
            result = await runtime_instance.execute([{"action": step.action_name, "args": step.arguments}])
            return {
                "success": True,
                "data": result,
                "runtime_used": selected_runtime_name,
                "capability_used": target_cap,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "runtime_used": selected_runtime_name,
            }
