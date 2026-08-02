"""
Integration Test — Sprint 15: Memory & Experience Pipeline.
Tests End-to-End Experience Learning:
Goal Execution -> Artifact Generation -> Experience Extraction -> Knowledge Graph Storage -> Reasoner Optimization.
"""

import asyncio
import pytest

from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.goals import GoalManager, GoalState, GoalType
from core.knowledge import (
    ExperienceExtractor,
    KnowledgeGraphReasoner,
    KnowledgeNodeType,
    SQLiteKnowledgeGraphStore,
)
from core.runtime.capability import CapabilityNegotiator
from core.vision import MockVisionAdapter


@pytest.mark.asyncio
async def test_end_to_end_experience_learning_pipeline():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    negotiator.register_runtime("desktop", desktop)
    negotiator.register_runtime("vision", vision)

    # Knowledge & Experience Subsystem
    store = SQLiteKnowledgeGraphStore(":memory:")
    extractor = ExperienceExtractor()
    reasoner = KnowledgeGraphReasoner(store)

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)

    # 1. Execute Goal #1
    goal1 = await manager.create_goal("Download monthly report and verify via vision", goal_type=GoalType.BROWSER)
    res1 = await manager.start_goal(goal1.id)
    assert res1.success is True
    assert goal1.artifact is not None

    # 2. Extract Experience from Goal #1
    exp_graph = extractor.extract_experience(goal1, goal1.artifact)
    for node in exp_graph.nodes.values():
        store.save_node(node)
    for edge in exp_graph.edges:
        store.save_edge(edge)

    # 3. Query Experience Reasoner for Goal #2
    rec_runtime = reasoner.recommend_runtime(goal_type="browser", intent="download monthly report")
    assert rec_runtime is not None

    rec_tool = reasoner.recommend_tool("click_download_button")
    assert rec_tool == "click"

    # 4. Verify stored experience nodes in graph
    stored_graph = store.get_graph()
    assert len(stored_graph.nodes) > 0
    assert len(stored_graph.edges) > 0

    await desktop.stop()
    await vision.shutdown()
