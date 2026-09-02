"""
Real User E2E Scenarios Test Suite — Sprint 14.5 Hardening.
Tests 4 critical production scenarios across Browser, Desktop, Vision, Goal Manager, and Telemetry.
"""

import asyncio
import pytest

from core.browser.adapters.playwright_adapter import PlaywrightAdapter
from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.goals import GoalManager, GoalState, GoalType
from core.runtime.capability import CapabilityNegotiator
from core.telemetry.benchmark import BenchmarkSuite
from core.telemetry.dashboard import TelemetryDashboard
from core.vision import MockVisionAdapter, VisualPlanner


class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def exception(self, msg): pass


@pytest.mark.asyncio
async def test_scenario_1_web_browser_flow():
    """
    Scenario 1: Web Browser Flow
    Open Browser -> Login -> Search -> Download -> Verify -> Complete
    """
    event_bus = EventBus()
    dashboard = TelemetryDashboard(event_bus)
    benchmark = BenchmarkSuite()

    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    negotiator.register_runtime("desktop", desktop)
    negotiator.register_runtime("vision", vision)

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)

    with benchmark.measure("goal_creation"):
        goal = await manager.create_goal(
            "Open Chrome, login to portal, search report, download sales.xlsx and verify",
            goal_type=GoalType.BROWSER,
        )

    with benchmark.measure("total_goal_time"):
        result = await manager.start_goal(goal.id)

    assert result.success is True
    assert goal.state == GoalState.COMPLETED
    assert goal.artifact is not None

    report = benchmark.get_benchmark_report()
    assert "goal_creation" in report
    assert "total_goal_time" in report

    await desktop.stop()
    await vision.shutdown()


@pytest.mark.asyncio
async def test_scenario_2_desktop_document_flow():
    """
    Scenario 2: Desktop Document Flow
    Open Excel/Notepad -> Read Data -> Save CSV -> Close Window
    """
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)

    await desktop.start()
    negotiator.register_runtime("desktop", desktop)

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
    goal = await manager.create_goal("Open Notepad, write data, save file to CSV and close window")

    result = await manager.start_goal(goal.id)
    assert result.success is True
    assert goal.state == GoalState.COMPLETED

    await desktop.stop()


@pytest.mark.asyncio
async def test_scenario_3_vision_fallback_and_recovery():
    """
    Scenario 3: Vision Fallback & Recovery
    Selector fails -> Vision OCR / VisualPlanner detects element -> Replanning -> Continue Goal
    """
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)
    vision = MockVisionAdapter()

    await desktop.start()
    await vision.start()

    negotiator.register_runtime("desktop", desktop)
    negotiator.register_runtime("vision", vision)

    # 1. Capture screen using Desktop
    shot = await desktop.screenshot.capture_screen()
    assert shot.success is True

    # 2. Vision Runtime analyzes screen
    obs = await vision.analyze_screenshot(shot.screenshot_base64)

    # 3. VisualPlanner finds target visually
    planner = VisualPlanner()
    target = planner.find_click_target(obs.semantic_graph, "Submit")
    assert target is not None

    # 4. Desktop executes resolved visual click
    click_res = await desktop.ui.click(target.x, target.y)
    assert click_res.success is True

    await desktop.stop()
    await vision.shutdown()


@pytest.mark.asyncio
async def test_scenario_4_interruption_pause_resume():
    """
    Scenario 4: Interruption & Context Resume
    Pause running goal -> Snapshot state -> Resume goal -> Complete
    """
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    desktop = MockDesktopAdapter(event_bus)

    await desktop.start()
    negotiator.register_runtime("desktop", desktop)

    manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
    goal = await manager.create_goal("Long desktop execution task")

    # Simulate pause at step 1
    goal.progress.current_step_index = 1
    goal.state = GoalState.RUNNING

    paused = await manager.pause_goal(goal.id)
    assert paused is True
    assert goal.state == GoalState.PAUSED

    # Resume goal execution
    result = await manager.resume_goal(goal.id)
    assert result.success is True
    assert goal.state == GoalState.COMPLETED

    await desktop.stop()
