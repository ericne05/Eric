"""
Planning Cognitive Agent.
Handles goal decomposition and execution plan construction.
Does NOT execute low-level actions.
"""

from typing import Optional

from core.cognition.enums import AgentRole, MessageType
from core.cognition.interfaces import ICognitiveAgent
from core.cognition.models import AgentMessage, CognitionResult, SharedCognitiveContext
from core.goals import AutonomousGoalPlanner, GoalDecomposer, GoalState


class PlanningAgent(ICognitiveAgent):
    """
    Planning Agent.
    Decomposes GoalSpecification into SubGoal DAG and builds capability-mapped ExecutionPlans.
    """

    def __init__(self, planner: Optional[AutonomousGoalPlanner] = None):
        self._planner = planner or AutonomousGoalPlanner(GoalDecomposer())

    @property
    def role(self) -> AgentRole:
        return AgentRole.PLANNER

    async def process_message(self, message: AgentMessage, context: SharedCognitiveContext) -> CognitionResult:
        if not context.goal:
            return CognitionResult(success=False, agent_role=self.role, error="No goal in context to plan")

        if not context.goal.plan or not context.goal.plan.steps:
            context.goal = self._planner.decompose(context.goal.spec)
            context.goal.plan = self._planner.build_plan(context.goal)
            context.goal.state = GoalState.READY

        return CognitionResult(
            success=True,
            agent_role=self.role,
            data={"plan_version": context.goal.plan.version, "step_count": len(context.goal.plan.steps)},
            suggested_action=f"Plan generated with {len(context.goal.plan.steps)} steps.",
        )
