"""
Execution Cognitive Agent.
The ONLY Cognitive Agent that dispatches steps to Runtimes via CapabilityNegotiator.
"""

from typing import Optional

from core.cognition.enums import AgentRole
from core.cognition.interfaces import ICognitiveAgent
from core.cognition.models import AgentMessage, CognitionResult, SharedCognitiveContext
from core.goals import GoalOrchestrator, GoalState
from core.runtime.capability import CapabilityNegotiator


class ExecutionAgent(ICognitiveAgent):
    """
    Execution Agent.
    Strictly dispatches ExecutionSteps to registered Runtimes using ONLY the CapabilityNegotiator.
    """

    def __init__(self, negotiator: CapabilityNegotiator):
        self._negotiator = negotiator
        self._orchestrator = GoalOrchestrator(negotiator)

    @property
    def role(self) -> AgentRole:
        return AgentRole.EXECUTION

    async def process_message(self, message: AgentMessage, context: SharedCognitiveContext) -> CognitionResult:
        goal = context.goal
        if not goal or not goal.plan:
            return CognitionResult(success=False, agent_role=self.role, error="No plan available to execute")

        goal.state = GoalState.RUNNING
        executed_steps = 0
        runtimes_used = []

        for step in goal.plan.steps:
            if step.status == "completed":
                continue

            step.status = "running"
            res = await self._orchestrator.execute_step(step)

            if res.get("success"):
                step.status = "completed"
                executed_steps += 1
                runtimes_used.append(res.get("runtime_used", "none"))
                context.record_history("step_completed", {"step_id": step.id, "action": step.action_name, "runtime": res.get("runtime_used")})
            else:
                step.status = "failed"
                context.record_history("step_failed", {"step_id": step.id, "action": step.action_name, "error": res.get("error")})
                return CognitionResult(
                    success=False,
                    agent_role=self.role,
                    error=res.get("error", "Step execution failed"),
                    data={"failed_step": step, "executed_steps": executed_steps},
                )

        goal.state = GoalState.COMPLETED
        return CognitionResult(
            success=True,
            agent_role=self.role,
            data={"executed_steps": executed_steps, "runtimes_used": runtimes_used},
            suggested_action=f"Successfully executed {executed_steps} steps across {set(runtimes_used)}.",
        )
