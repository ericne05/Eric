"""
Knowledge & Experience Graph Reasoner.
Provides 8 recommendation engines for experience-driven zero-shot optimization.
"""

from typing import Any, Dict, List, Optional

from core.goals.models import GoalSpecification
from core.knowledge.enums import KnowledgeNodeType, KnowledgeRelationType
from core.knowledge.interfaces import IKnowledgeGraphStore, IKnowledgeReasoner
from core.knowledge.models import KnowledgeGraph, KnowledgeNode


class KnowledgeGraphReasoner(IKnowledgeReasoner):
    """
    Experience-Driven Reasoner.
    Queries the Knowledge & Experience Graph to recommend optimal runtimes, tools,
    recovery actions, parameters, and fast execution paths based on past experience.
    """

    def __init__(self, store: IKnowledgeGraphStore):
        self._store = store

    def _get_graph(self) -> KnowledgeGraph:
        return self._store.get_graph()

    def recommend_runtime(self, goal_type: str, intent: str) -> Optional[str]:
        graph = self._store.get_graph()
        runtimes = graph.find_nodes_by_type(KnowledgeNodeType.RUNTIME)

        if not runtimes:
            intent_lower = intent.lower()
            if "browser" in intent_lower or "download" in intent_lower or "web" in intent_lower:
                return "browser"
            elif "ocr" in intent_lower or "see" in intent_lower or "image" in intent_lower:
                return "vision"
            return "desktop"

        best = max(runtimes, key=lambda n: n.experience_score * n.success_rate)
        return best.name

    def recommend_tool(self, subgoal_title: str) -> Optional[str]:
        graph = self._store.get_graph()
        tools = graph.find_nodes_by_type(KnowledgeNodeType.TOOL)
        title_lower = subgoal_title.lower()

        for t in tools:
            if t.name.lower() in title_lower or title_lower in t.name.lower():
                return t.name

        if "click" in title_lower:
            return "click"
        elif "open" in title_lower or "navigate" in title_lower:
            return "navigate"
        elif "see" in title_lower or "ocr" in title_lower:
            return "ocr"
        return "click"

    def recommend_recovery(self, error_type: str) -> Optional[str]:
        graph = self._store.get_graph()
        errors = graph.find_nodes_by_type(KnowledgeNodeType.ERROR)

        for err in errors:
            if error_type.lower() in err.name.lower() or error_type.lower() in str(err.attributes).lower():
                for edge in graph.get_outgoing_edges(err.id):
                    if edge.relation_type == KnowledgeRelationType.RECOVERED_BY:
                        target = graph.nodes.get(edge.target_id)
                        if target:
                            return target.name
        return "vision_ocr_fallback"

    def recommend_parameters(self, intent: str) -> Dict[str, Any]:
        graph = self._store.get_graph()
        intent_lower = intent.lower()

        for node in graph.nodes.values():
            if node.node_type in (KnowledgeNodeType.PATTERN, KnowledgeNodeType.ENTITY):
                node_intent = node.attributes.get("intent", "").lower()
                if intent_lower in node_intent or node_intent in intent_lower:
                    return {"cached_params": node.attributes, "confidence": node.success_rate}

        return {"confidence": 0.5}

    def find_best_execution_path(self, spec: GoalSpecification) -> List[str]:
        graph = self._store.get_graph()
        patterns = self.find_success_pattern(spec.goal_type.value)

        if patterns:
            best_pattern = max(patterns, key=lambda p: p.experience_score)
            steps = []
            for edge in graph.get_outgoing_edges(best_pattern.id):
                if edge.relation_type == KnowledgeRelationType.HAS_STEP:
                    tgt = graph.nodes.get(edge.target_id)
                    if tgt:
                        steps.append(tgt.name)
            if steps:
                return steps

        return ["observe_environment", "execute_desktop_action"]

    def find_related_goal(self, intent: str) -> Optional[KnowledgeNode]:
        graph = self._store.get_graph()
        intent_lower = intent.lower()

        for node in graph.nodes.values():
            if node.node_type in (KnowledgeNodeType.PATTERN, KnowledgeNodeType.ENTITY, KnowledgeNodeType.GOAL_ARTIFACT):
                if intent_lower in node.name.lower() or intent_lower in str(node.attributes).lower():
                    return node
        return None

    def find_success_pattern(self, goal_type: str) -> List[KnowledgeNode]:
        graph = self._store.get_graph()
        return [
            n for n in graph.find_nodes_by_type(KnowledgeNodeType.PATTERN)
            if n.success_rate >= 0.8 and n.attributes.get("goal_type") == goal_type
        ]

    def find_failure_pattern(self, goal_type: str) -> List[KnowledgeNode]:
        graph = self._store.get_graph()
        return [
            n for n in graph.nodes.values()
            if n.success_rate < 0.5 and n.attributes.get("goal_type") == goal_type
        ]
