"""
Coordinator Policies (Sequential, Parallel, Priority).
"""

from typing import List

from core.cognition.enums import AgentRole
from core.cognition.interfaces import ICognitiveAgent, ICoordinatorPolicy


class SequentialPolicy(ICoordinatorPolicy):
    """
    Executes agents in strict cognitive sequence:
    KnowledgeAgent -> PlanningAgent -> ExecutionAgent -> RecoveryAgent (if needed).
    """

    def select_execution_order(self, agents: List[ICognitiveAgent]) -> List[ICognitiveAgent]:
        role_priority = {
            AgentRole.KNOWLEDGE: 1,
            AgentRole.PLANNER: 2,
            AgentRole.EXECUTION: 3,
            AgentRole.RECOVERY: 4,
        }
        return sorted(agents, key=lambda a: role_priority.get(a.role, 99))


class ParallelPolicy(ICoordinatorPolicy):
    """Executes agents concurrently where applicable."""

    def select_execution_order(self, agents: List[ICognitiveAgent]) -> List[ICognitiveAgent]:
        return agents


class PriorityPolicy(ICoordinatorPolicy):
    """Executes higher priority role first."""

    def select_execution_order(self, agents: List[ICognitiveAgent]) -> List[ICognitiveAgent]:
        return sorted(agents, key=lambda a: a.role.value)
