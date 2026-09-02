"""
Cognitive Coordinator (Sprint 16 Product-Grade).
Orchestrates Cognitive Agents (Knowledge, Planning, Execution, Recovery) via CoordinatorPolicy.
"""

from typing import List, Optional

from core.cognition.enums import AgentRole, MessageType
from core.cognition.execution_agent import ExecutionAgent
from core.cognition.interfaces import ICognitiveAgent, ICognitiveCoordinator, ICoordinatorPolicy
from core.cognition.knowledge_agent import KnowledgeAgent
from core.cognition.messaging import CognitiveMessageBus
from core.cognition.models import AgentMessage, CognitionResult, SharedCognitiveContext
from core.cognition.planning_agent import PlanningAgent
from core.cognition.policies import SequentialPolicy
from core.cognition.recovery_agent import RecoveryAgent
from core.goals.models import GoalResult
from core.runtime.capability import CapabilityNegotiator


class CognitiveCoordinator(ICognitiveCoordinator):
    """
    Cognitive Coordinator.
    Main controller for the Cognitive Coordination Layer (`core/cognition/`).
    Does NOT execute actions directly. Coordinates Cognitive Agents via CoordinatorPolicy.
    """

    def __init__(
        self,
        negotiator: CapabilityNegotiator,
        policy: Optional[ICoordinatorPolicy] = None,
        bus: Optional[CognitiveMessageBus] = None,
    ):
        self._negotiator = negotiator
        self._policy = policy or SequentialPolicy()
        self._bus = bus or CognitiveMessageBus()

        self._knowledge_agent = KnowledgeAgent()
        self._planning_agent = PlanningAgent()
        self._execution_agent = ExecutionAgent(negotiator)
        self._recovery_agent = RecoveryAgent()

        self._agents: List[ICognitiveAgent] = [
            self._knowledge_agent,
            self._planning_agent,
            self._execution_agent,
            self._recovery_agent,
        ]

    async def run_cognition_loop(self, context: SharedCognitiveContext) -> CognitionResult:
        if not context.goal:
            return CognitionResult(success=False, agent_role=AgentRole.COORDINATOR, error="No goal provided in SharedCognitiveContext")

        from core.goals.enums import GoalState
        if context.goal.state == GoalState.PAUSED:
            return CognitionResult(success=False, agent_role=AgentRole.COORDINATOR, error="Goal is paused")
        if context.goal.state == GoalState.CANCELLED:
            return CognitionResult(success=False, agent_role=AgentRole.COORDINATOR, error="Goal is cancelled")

        context.goal.state = GoalState.RUNNING
        ordered_agents = self._policy.select_execution_order(self._agents)

        # 1. Knowledge Phase
        msg_know = AgentMessage(sender_role=AgentRole.COORDINATOR, target_role=AgentRole.KNOWLEDGE, message_type=MessageType.TASK_REQUEST)
        res_know = await self._knowledge_agent.process_message(msg_know, context)

        # 2. Planning Phase
        msg_plan = AgentMessage(sender_role=AgentRole.COORDINATOR, target_role=AgentRole.PLANNER, message_type=MessageType.TASK_REQUEST)
        res_plan = await self._planning_agent.process_message(msg_plan, context)

        if not res_plan.success:
            context.goal.state = GoalState.FAILED
            return res_plan

        # 3. Execution Phase
        msg_exec = AgentMessage(sender_role=AgentRole.COORDINATOR, target_role=AgentRole.EXECUTION, message_type=MessageType.TASK_REQUEST)
        res_exec = await self._execution_agent.process_message(msg_exec, context)

        if res_exec.success:
            context.goal.state = GoalState.COMPLETED
            # Attach GoalResult
            context.goal.result = GoalResult(success=True, goal_id=context.goal.id, summary="Executed via Cognitive Coordination Layer")
            return res_exec

        # 4. Recovery Phase if execution failed
        msg_rec = AgentMessage(
            sender_role=AgentRole.COORDINATOR,
            target_role=AgentRole.RECOVERY,
            message_type=MessageType.RECOVERY_PROPOSAL,
            payload={"error": res_exec.error, "failed_step": res_exec.data.get("failed_step") if res_exec.data else None},
        )
        res_rec = await self._recovery_agent.process_message(msg_rec, context)

        if res_rec.success and res_rec.data and res_rec.data.get("decision") == "replan":
            # Retry execution phase with replanned plan
            retry_res = await self._execution_agent.process_message(msg_exec, context)
            if retry_res.success:
                context.goal.state = GoalState.COMPLETED
            else:
                context.goal.state = GoalState.FAILED
            return retry_res

        context.goal.state = GoalState.FAILED
        return res_rec
