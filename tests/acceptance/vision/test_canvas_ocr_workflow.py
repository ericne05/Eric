"""
Vision & Canvas Acceptance Tests (Non-standard Canvas UI, OCR Parse, Visual Fallback).
"""

import pytest

from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.vision import MockVisionAdapter, VisualPlanner


@pytest.mark.asyncio
async def test_vision_canvas_ocr_workflow():
    """
    Workflow: Canvas UI -> OCR Parsing -> Visual Coordinate Resolution -> Action Execution
    """
    event_bus = EventBus()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    shot = await desktop.screenshot.capture_screen()
    assert shot.success is True

    obs = await vision.analyze_screenshot(shot.screenshot_base64)
    planner = VisualPlanner()
    target = planner.find_click_target(obs.semantic_graph, "Submit")

    assert target is not None
    click_res = await desktop.ui.click(target.x, target.y)
    assert click_res.success is True

    await desktop.stop()
    await vision.shutdown()
