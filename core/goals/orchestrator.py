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

    def __init__(self, negotiator: CapabilityNegotiator):
        self._negotiator = negotiator

    async def execute_step(self, step: ExecutionStep) -> Dict[str, Any]:
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
