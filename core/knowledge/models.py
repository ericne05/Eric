"""
Knowledge & Experience Graph Models (Sprint 15).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from core.knowledge.enums import KnowledgeNodeType, KnowledgeRelationType


@dataclass
class ExperienceScore:
    """Calculates quantitative experience score for goal executions."""
    success: bool = True
    token_cost: int = 0
    duration_seconds: float = 0.0
    recovery_count: int = 0
    raw_score: float = 100.0

    def calculate(self) -> float:
        base = 100.0 if self.success else 0.0
        penalty = (self.recovery_count * 15.0) + (self.duration_seconds * 2.0) + (self.token_cost * 0.1)
        self.raw_score = max(0.0, min(100.0, base - penalty))
        return round(self.raw_score, 1)


@dataclass
class KnowledgeNode:
    """Node in the Knowledge & Experience Graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: KnowledgeNodeType = KnowledgeNodeType.ENTITY
    name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 1
    success_rate: float = 1.0
    experience_score: float = 100.0
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    def record_usage(self, success: bool, score: float = 100.0) -> None:
        """Updates usage count, running success rate, and experience score."""
        self.usage_count += 1
        alpha = 0.2  # Moving average weight
        new_success = 1.0 if success else 0.0
        self.success_rate = round((1 - alpha) * self.success_rate + alpha * new_success, 2)
        self.experience_score = round((1 - alpha) * self.experience_score + alpha * score, 1)


@dataclass
class KnowledgeEdge:
    """Directed edge representing relationships and experience confidence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: KnowledgeRelationType = KnowledgeRelationType.HAS_STEP
    confidence: float = 0.9  # 0.0 to 1.0
    weight: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    def update_confidence(self, success: bool) -> None:
        """Increases confidence on success, decreases on failure."""
        if success:
            self.confidence = min(1.0, round(self.confidence + 0.05, 2))
        else:
            self.confidence = max(0.1, round(self.confidence - 0.2, 2))


@dataclass
class KnowledgeGraph:
    """In-memory Knowledge & Experience Graph representation."""
    nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: List[KnowledgeEdge] = field(default_factory=list)

    def add_node(self, node: KnowledgeNode) -> None:
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: KnowledgeRelationType,
        confidence: float = 0.9,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEdge:
        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
            attributes=attributes or {},
        )
        self.edges.append(edge)
        return edge

    def find_nodes_by_type(self, node_type: KnowledgeNodeType) -> List[KnowledgeNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def find_node_by_name(self, name: str) -> Optional[KnowledgeNode]:
        name_lower = name.lower()
        for node in self.nodes.values():
            if node.name.lower() == name_lower:
                return node
        return None

    def get_outgoing_edges(self, source_id: str) -> List[KnowledgeEdge]:
        return [e for e in self.edges if e.source_id == source_id]
