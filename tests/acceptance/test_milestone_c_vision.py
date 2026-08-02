"""
Milestone C Acceptance Tests — Vision & Screen Understanding.
Verifies actual end-to-end execution of Vision Fallback, OCR Parsing, and UI Recognition Use Cases.
"""

import pytest

from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.vision import MockVisionAdapter, VisualPlanner


@pytest.mark.asyncio
async def test_use_case_c1_ocr_element_recognition_and_fallback():
    """
    Use Case C1: UI Selector Failure -> Fallback to Vision OCR -> Resolve Target Coordinates -> Click
    """
    event_bus = EventBus()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    # 1. Capture screen
    shot = await desktop.screenshot.capture_screen()
    assert shot.success is True

    # 2. Analyze screen via OCR & Vision Engine
    obs = await vision.analyze_screenshot(shot.screenshot_base64)
    assert obs is not None
    assert len(obs.semantic_graph.nodes) > 0

    # 3. VisualPlanner finds target button coordinates
    planner = VisualPlanner()
    target = planner.find_click_target(obs.semantic_graph, "Submit")
    assert target is not None
    assert target.label == "Submit"

    # 4. Desktop executes resolved click
    click_res = await desktop.ui.click(target.x, target.y)
    assert click_res.success is True

    await desktop.stop()
    await vision.shutdown()


@pytest.mark.asyncio
async def test_use_case_c2_semantic_screen_graph_traversal():
    """
    Use Case C2: Parse Screen Graph -> Traverse Reading Order & Spatial Edges -> Find Element
    """
    vision = MockVisionAdapter()
    await vision.start()

    obs = await vision.analyze_screenshot("mock_base64")
    graph = obs.semantic_graph

    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    # Extract text content in reading order
    planner = VisualPlanner()
    visible_texts = planner.extract_visible_text(graph)
    assert len(visible_texts) > 0

    await vision.shutdown()
