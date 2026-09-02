"""
Unit Tests for Sprint 15 — Knowledge & Experience Graph Subsystem.
"""

import pytest

from core.goals import Goal, GoalArtifact, GoalResult, GoalSpecification, GoalType
from core.knowledge import (
    ExperienceExtractor,
    ExperienceScore,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeGraphReasoner,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelationType,
    SQLiteKnowledgeGraphStore,
)


def test_experience_score_calculator():
    score_obj = ExperienceScore(
        success=True,
        token_cost=50,
        duration_seconds=2.5,
        recovery_count=1,
    )
    score = score_obj.calculate()
    # 100 - (1 * 15) - (2.5 * 2) - (50 * 0.1) = 100 - 15 - 5 - 5 = 75.0
    assert score == 75.0


def test_knowledge_node_and_edge():
    node = KnowledgeNode(name="Chrome Browser", node_type=KnowledgeNodeType.ENVIRONMENT)
    node.record_usage(success=True, score=95.0)
    assert node.usage_count == 2
    assert node.success_rate > 0.9

    edge = KnowledgeEdge(source_id="n1", target_id="n2", relation_type=KnowledgeRelationType.USES_RUNTIME, confidence=0.8)
    edge.update_confidence(success=True)
    assert edge.confidence == 0.85
    edge.update_confidence(success=False)
    assert edge.confidence == 0.65


def test_sqlite_knowledge_graph_store():
    store = SQLiteKnowledgeGraphStore(":memory:")
    node1 = KnowledgeNode(id="n1", name="Excel", node_type=KnowledgeNodeType.ENVIRONMENT)
    node2 = KnowledgeNode(id="n2", name="Export Step", node_type=KnowledgeNodeType.TOOL)
    edge = KnowledgeEdge(id="e1", source_id="n1", target_id="n2", relation_type=KnowledgeRelationType.USES_TOOL)

    store.save_node(node1)
    store.save_node(node2)
    store.save_edge(edge)

    retrieved = store.get_node("n1")
    assert retrieved is not None
    assert retrieved.name == "Excel"

    graph = store.get_graph()
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1


def test_experience_extractor():
    extractor = ExperienceExtractor()

    spec = GoalSpecification(title="Export Monthly Financials", intent="Download excel sales", goal_type=GoalType.BROWSER)
    goal = Goal(spec=spec)
    goal.result = GoalResult(success=True, goal_id=goal.id, summary="Downloaded sales.xlsx")

    artifact = GoalArtifact(goal_id=goal.id, title="Sales Report Artifact", summary="Exported 500 rows")
    goal.artifact = artifact

    extracted_graph = extractor.extract_experience(goal, artifact)

    assert len(extracted_graph.nodes) >= 3
    nodes_types = [n.node_type for n in extracted_graph.nodes.values()]
    assert KnowledgeNodeType.PATTERN in nodes_types or KnowledgeNodeType.ENTITY in nodes_types
    assert KnowledgeNodeType.ENVIRONMENT in nodes_types
    assert KnowledgeNodeType.GOAL_ARTIFACT in nodes_types


def test_knowledge_graph_reasoner_8_engines():
    store = SQLiteKnowledgeGraphStore(":memory:")
    reasoner = KnowledgeGraphReasoner(store)

    # 1. Recommend Runtime
    runtime = reasoner.recommend_runtime("browser", "download sales report")
    assert runtime in ("browser", "desktop", "vision")

    # 2. Recommend Tool
    tool = reasoner.recommend_tool("click_submit_button")
    assert tool == "click"

    # 3. Recommend Recovery
    recovery = reasoner.recommend_recovery("SelectorNotFound")
    assert recovery == "vision_ocr_fallback"

    # 4. Recommend Parameters
    params = reasoner.recommend_parameters("download report")
    assert "confidence" in params

    # 5. Best Execution Path
    path = reasoner.find_best_execution_path(GoalSpecification(goal_type=GoalType.BROWSER))
    assert len(path) >= 2

    # 6. Related Goal
    related = reasoner.find_related_goal("download")
    assert related is None or isinstance(related, KnowledgeNode)

    # 7. Success Pattern
    success_patterns = reasoner.find_success_pattern("browser")
    assert isinstance(success_patterns, list)

    # 8. Failure Pattern
    failure_patterns = reasoner.find_failure_pattern("browser")
    assert isinstance(failure_patterns, list)
