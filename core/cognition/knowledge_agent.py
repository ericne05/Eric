"""
Knowledge Cognitive Agent.
Handles Knowledge Graph query, experience lookup, and recommendation proposals.
Does NOT execute low-level actions.
"""

from typing import Optional

from core.cognition.enums import AgentRole, MessageType
from core.cognition.interfaces import ICognitiveAgent
from core.cognition.models import AgentMessage, CognitionResult, SharedCognitiveContext
from core.knowledge import KnowledgeGraphReasoner, SQLiteKnowledgeGraphStore


class KnowledgeAgent(ICognitiveAgent):
    """
    Knowledge Agent.
    Provides experience lookup, pattern recommendations, and parameter caching.
    """

    def __init__(self, reasoner: Optional[KnowledgeGraphReasoner] = None):
        self._reasoner = reasoner or KnowledgeGraphReasoner(SQLiteKnowledgeGraphStore(":memory:"))

    @property
    def role(self) -> AgentRole:
        return AgentRole.KNOWLEDGE

    async def process_message(self, message: AgentMessage, context: SharedCognitiveContext) -> CognitionResult:
        if not context.goal:
            return CognitionResult(success=False, agent_role=self.role, error="No active goal in context")

        intent = context.goal.spec.intent or context.goal.spec.description
        rec_runtime = self._reasoner.recommend_runtime(context.goal.spec.goal_type.value, intent)
        related_node = self._reasoner.find_related_goal(intent)

        suggestion = f"Recommended runtime: {rec_runtime}."
        if related_node:
            suggestion += f" Found related pattern: {related_node.name}"

        return CognitionResult(
            success=True,
            agent_role=self.role,
            data={"recommended_runtime": rec_runtime, "related_node": related_node},
            suggested_action=suggestion,
        )
