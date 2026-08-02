"""
Recovery Cognitive Agent.
Handles failure recovery decisions: Retry, Replan, Ask User, or Abort.
Does NOT execute low-level actions directly.
"""

from typing import Optional

from core.cognition.enums import AgentRole
from core.cognition.interfaces import ICognitiveAgent
from core.cognition.models import AgentMessage, CognitionResult, SharedCognitiveContext
from core.goals import DynamicReplanner, GoalRecoveryManager, GoalState, StepPolicy


class RecoveryAgent(ICognitiveAgent):
    """
    Recovery Agent.
    Evaluates execution failures and chooses Recovery Proposals (Retry / Replan / AskUser / Abort).
    """

    def __init__(self, recovery_manager: Optional[GoalRecoveryManager] = None):
        self._manager = recovery_manager or GoalRecoveryManager()
        self._replanner = DynamicReplanner()

    @property
    def role(self) -> AgentRole:
        return AgentRole.RECOVERY

    async def process_message(self, message: AgentMessage, context: SharedCognitiveContext) -> CognitionResult:
        goal = context.goal
        if not goal:
            return CognitionResult(success=False, agent_role=self.role, error="No goal in context")

        error_msg = message.payload.get("error", "Unknown execution error")
        failed_step = message.payload.get("failed_step")

        if failed_step:
            new_state, policy = self._manager.handle_step_failure(goal, failed_step, error_msg)

            if policy == StepPolicy.RECOVER:
                goal.plan = self._replanner.replan(goal, failed_step, error_msg)
                goal.state = GoalState.RUNNING
                return CognitionResult(
                    success=True,
                    agent_role=self.role,
                    data={"decision": "replan", "new_version": goal.plan.version},
                    suggested_action=f"Replanned execution plan to version {goal.plan.version}.",
                )
            elif policy == StepPolicy.ASK_USER:
                goal.state = GoalState.WAITING
                return CognitionResult(
                    success=True,
                    agent_role=self.role,
                    data={"decision": "ask_user"},
                    suggested_action="Requested user confirmation before proceeding.",
                )

        goal.state = GoalState.FAILED
        return CognitionResult(
            success=False,
            agent_role=self.role,
            error=error_msg,
            data={"decision": "abort"},
            suggested_action="Aborted goal execution due to unrecoverable failure.",
        )
