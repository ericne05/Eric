"""
Integration Test — Sprint 13: Desktop → Screenshot → Vision → Planner → Desktop

Tests the full realistic pipeline:
  1. Desktop Runtime captures a screenshot.
  2. Vision Runtime analyzes the screenshot, builds a SemanticScreenGraph.
  3. VisualPlanner queries the graph for a click target.
  4. Desktop Runtime executes the click at the resolved coordinates.
  5. EventBus events flow correctly through the entire chain.
"""

import asyncio
import pytest

from core.desktop import MockDesktopAdapter
from core.events.event import Event
from core.events.event_bus import EventBus
from core.runtime.capability import CapabilityNegotiator
from core.telemetry.dashboard import TelemetryDashboard
from core.vision import MockVisionAdapter, VisualPlanner


@pytest.mark.asyncio
async def test_desktop_vision_pipeline_end_to_end():
    """
    Full pipeline: Desktop → Screenshot → Vision → Planner → Desktop click.
    """
    event_bus = EventBus()
    events_captured = []
    event_bus.subscribe("desktop.action.*", lambda e: events_captured.append(e.name))

    desktop = MockDesktopAdapter(event_bus=event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    # Step 1: Desktop Runtime captures a screenshot
    screenshot_result = await desktop.screenshot.capture_screen()
    assert screenshot_result.success is True
    screenshot_b64 = screenshot_result.screenshot_base64
    assert screenshot_b64 is not None

    # Step 2: Vision Runtime analyzes the screenshot → SemanticScreenGraph
    observation = await vision.analyze_screenshot(screenshot_b64)
    assert observation.semantic_graph.node_count > 0
    assert observation.ocr_result.full_text != ""

    # Step 3: VisualPlanner queries graph for "Submit" button
    planner = VisualPlanner()
    target = planner.find_click_target(observation.semantic_graph, "Submit")
    assert target is not None, "VisualPlanner must find the Submit button"
    assert target.x > 0 and target.y > 0
    assert target.confidence > 0.5

    # Step 4: Desktop Runtime executes the click at resolved coordinates
    click_result = await desktop.ui.click(target.x, target.y)
    assert click_result.success is True
    assert click_result.data["x"] == target.x
    assert click_result.data["y"] == target.y

    await desktop.stop()
    await vision.shutdown()

    # Step 5: Verify EventBus events fired for the click
    assert "desktop.action.started" in events_captured
    assert "desktop.action.completed" in events_captured


@pytest.mark.asyncio
async def test_capability_negotiator_routes_to_correct_runtime():
    """
    Planner uses CapabilityNegotiator to decide which runtime handles OCR
    vs mouse actions — each routed to the right subsystem.
    """
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    negotiator.register_runtime("desktop", MockDesktopAdapter(event_bus))
    negotiator.register_runtime("vision", MockVisionAdapter())

    # OCR must route to Vision, not Desktop
    ocr_providers = negotiator.find_runtimes_supporting("ocr")
    assert ocr_providers == ["vision"]

    # Mouse must route to Desktop, not Vision
    mouse_providers = negotiator.find_runtimes_supporting("mouse")
    assert mouse_providers == ["desktop"]

    # Both support screenshot
    screenshot_providers = negotiator.find_runtimes_supporting("screenshot")
    assert "desktop" in screenshot_providers
    assert "vision" in screenshot_providers


@pytest.mark.asyncio
async def test_pipeline_with_telemetry_dashboard():
    """
    Full pipeline with TelemetryDashboard collecting metrics.
    After the pipeline, verify the dashboard captures the action events.
    """
    event_bus = EventBus()
    dashboard = TelemetryDashboard(event_bus)

    desktop = MockDesktopAdapter(event_bus=event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    # Run pipeline
    screenshot = await desktop.screenshot.capture_screen()
    obs = await vision.analyze_screenshot(screenshot.screenshot_base64)
    planner = VisualPlanner()
    target = planner.find_click_target(obs.semantic_graph, "Cancel")
    assert target is not None

    await desktop.ui.click(target.x, target.y)
    await desktop.ui.type_text("Hello from pipeline")

    await desktop.stop()
    await vision.shutdown()

    # Dashboard should have recorded both click and type actions
    snap = dashboard.snapshot()
    assert snap.total_actions >= 2
    assert snap.successful_actions >= 2
    assert snap.success_rate == 1.0


@pytest.mark.asyncio
async def test_vision_fallback_when_selector_fails():
    """
    Simulates a UIAutomation selector failure: Desktop can't find element
    by standard selector, so Vision Runtime steps in to locate the element
    visually via SemanticScreenGraph.
    """
    desktop = MockDesktopAdapter()
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    # UIAutomation path: element NOT found (simulated)
    uia_selector_found = False  # Simulates UIAutomation returning nothing

    if not uia_selector_found:
        # Fallback: Vision path
        screenshot = await desktop.screenshot.capture_screen()
        obs = await vision.analyze_screenshot(screenshot.screenshot_base64)
        planner = VisualPlanner()
        target = planner.find_click_target(obs.semantic_graph, "Submit")

        assert target is not None
        result = await desktop.ui.click(target.x, target.y)
        assert result.success is True

    await desktop.stop()
    await vision.shutdown()
