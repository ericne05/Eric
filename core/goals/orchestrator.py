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
    Never hardcodes Runtime instances or names.
    """

    def __init__(self, negotiator: CapabilityNegotiator):
        self._negotiator = negotiator

    async def execute_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """
        Queries CapabilityNegotiator for a Runtime supporting step.capability_required,
        and dispatches step execution.
        """
        cap = step.capability_required
        if not cap:
            cap = "mouse"  # Default capability fallback

        matching_runtimes = self._negotiator.find_runtimes_supporting(cap)

        if not matching_runtimes:
            # Try fallback capability query
            matching_runtimes = self._negotiator.find_runtimes_supporting("screenshot")

        if not matching_runtimes:
            return {
                "success": False,
                "error": f"No registered Runtime supports required capability '{cap}'",
                "runtime_used": "none",
            }

        selected_runtime_name = matching_runtimes[0]
        runtime_instance = self._negotiator._runtimes.get(selected_runtime_name)

        if not runtime_instance:
            return {"success": False, "error": f"Runtime '{selected_runtime_name}' not accessible", "runtime_used": selected_runtime_name}

        # Dispatch via IRuntime.execute
        try:
            result = await runtime_instance.execute([{"action": step.action_name, "args": step.arguments}])
            return {
                "success": True,
                "data": result,
                "runtime_used": selected_runtime_name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "runtime_used": selected_runtime_name,
            }
