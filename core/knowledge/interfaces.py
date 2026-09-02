"""
Knowledge & Experience Graph Interfaces (Sprint 15).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.goals.models import Goal, GoalArtifact, GoalSpecification
from core.knowledge.models import (
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelationType,
)


class IKnowledgeGraphStore(ABC):
    """Interface for persistent Knowledge & Experience Graph Storage."""

    @abstractmethod
    def save_node(self, node: KnowledgeNode) -> None:
        pass

    @abstractmethod
    def save_edge(self, edge: KnowledgeEdge) -> None:
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        pass

    @abstractmethod
    def query_nodes(self, node_type: KnowledgeNodeType) -> List[KnowledgeNode]:
        pass

    @abstractmethod
    def get_graph(self) -> KnowledgeGraph:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class IKnowledgeExtractor(ABC):
    """Interface for extracting Experience and Knowledge from executed Goals & Artifacts."""

    @abstractmethod
    def extract_experience(self, goal: Goal, artifact: Optional[GoalArtifact] = None) -> KnowledgeGraph:
        pass


class IKnowledgeReasoner(ABC):
    """
    Interface for Experience-Driven Reasoning & Optimization Engine.
    Provides 8 recommendation engines for zero-shot goal optimization.
    """

    @abstractmethod
    def recommend_runtime(self, goal_type: str, intent: str) -> Optional[str]:
        pass

    @abstractmethod
    def recommend_tool(self, subgoal_title: str) -> Optional[str]:
        pass

    @abstractmethod
    def recommend_recovery(self, error_type: str) -> Optional[str]:
        pass

    @abstractmethod
    def recommend_parameters(self, intent: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def find_best_execution_path(self, spec: GoalSpecification) -> List[str]:
        pass

    @abstractmethod
    def find_related_goal(self, intent: str) -> Optional[KnowledgeNode]:
        pass

    @abstractmethod
    def find_success_pattern(self, goal_type: str) -> List[KnowledgeNode]:
        pass

    @abstractmethod
    def find_failure_pattern(self, goal_type: str) -> List[KnowledgeNode]:
        pass
