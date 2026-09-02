"""
Unit tests for Sprint 12 - Desktop Automation Subsystem.
"""

import asyncio
import pytest

from core.browser.enums import WorkflowState
from core.desktop import (
    DesktopAction,
    DesktopActionQueue,
    DesktopMemoryPipeline,
    DesktopRecoveryManager,
    DesktopWorkflow,
    HybridDesktopPlanner,
    MockDesktopAdapter,
    UIAccessibilitySnapshot,
)
from core.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_mock_adapter_lifecycle_and_events():
    event_bus = EventBus()
    events_captured = []
    event_bus.subscribe("desktop.state.changed", lambda e: events_captured.append(e))

    adapter = MockDesktopAdapter(event_bus=event_bus)
    await adapter.start()
    assert len(events_captured) == 1
    assert events_captured[0].payload["state"] == "ready"

    await adapter.stop()
    assert len(events_captured) == 2
    assert events_captured[1].payload["state"] == "stopped"


@pytest.mark.asyncio
async def test_mock_ui_actions():
    event_bus = EventBus()
    events = []
    event_bus.subscribe("desktop.action.started", lambda e: events.append(e))
    event_bus.subscribe("desktop.action.completed", lambda e: events.append(e))

    adapter = MockDesktopAdapter(event_bus=event_bus)
    res_click = await adapter.ui.click(100, 200)
    assert res_click.success is True
    assert res_click.data["x"] == 100

    res_type = await adapter.ui.type_text("Hello Eric")
    assert res_type.success is True
    assert res_type.data["text"] == "Hello Eric"

    res_hotkey = await adapter.ui.hotkey("ctrl", "c")
    assert res_hotkey.success is True
    assert res_hotkey.data["keys"] == ["ctrl", "c"]

    assert len(events) == 6  # 3 started + 3 completed


@pytest.mark.asyncio
async def test_window_manager():
    adapter = MockDesktopAdapter()
    windows = await adapter.window_manager.get_active_windows()
    assert len(windows) == 2

    focused = await adapter.window_manager.get_focused_window()
    assert focused is not None
    assert focused.title == "Notepad"

    success = await adapter.window_manager.focus_window("w2")
    assert success is True
    focused_updated = await adapter.window_manager.get_focused_window()
    assert focused_updated.title == "File Explorer"


def test_action_queue_dag_and_cascading_cancellation():
    queue = DesktopActionQueue()

    act1 = DesktopAction(id="a1", name="open_app", priority=5)
    act2 = DesktopAction(id="a2", name="click_button", priority=10, dependencies=["a1"])
    act3 = DesktopAction(id="a3", name="type_input", priority=1, dependencies=["a2"])

    queue.add_action(act1)
    queue.add_action(act2)
    queue.add_action(act3)

    # Initially only act1 is ready because act2 depends on act1
    ready = queue.get_next_ready_action()
    assert ready is not None
    assert ready.id == "a1"

    # Mark a1 completed
    queue.mark_completed("a1")
    ready2 = queue.get_next_ready_action()
    assert ready2 is not None
    assert ready2.id == "a2"

    # Test cascading cancellation: fail a2, should cancel a3
    cancelled = queue.mark_failed("a2")
    assert "a2" in cancelled
    assert "a3" in cancelled
    assert queue.pending_count == 0


def test_desktop_recovery_manager():
    recovery = DesktopRecoveryManager(max_recovery_attempts=2)
    wf = DesktopWorkflow(goal="Open File")
    act = DesktopAction(id="act1", name="click_file", max_retries=2)

    state = recovery.handle_action_failure(wf, act, "Element not found")
    assert state == WorkflowState.RECOVERING
    assert wf.state == WorkflowState.RECOVERING
    assert wf.intelligence.planner_confidence.score < 1.0

    # Exhaust retries
    recovery.handle_action_failure(wf, act, "Element not found again")
    state_final = recovery.handle_action_failure(wf, act, "Third failure")
    assert state_final == WorkflowState.FAILED
    assert wf.state == WorkflowState.FAILED


def test_desktop_memory_pipeline():
    pipeline = DesktopMemoryPipeline()
    snapshot = UIAccessibilitySnapshot(
        tree_data={
            "children": [
                {"role": "button", "name": "Submit", "bounds": "10,20,100,40"},
                {"role": "edit", "name": "Username", "bounds": "10,70,200,30", "text": "john_doe"},
            ]
        }
    )

    chunks = pipeline.process_snapshot(snapshot, window_title="Settings Window")
    assert len(chunks) == 2
    assert "Submit" in chunks[0]["content"]
    assert chunks[1]["metadata"]["window_title"] == "Settings Window"


def test_hybrid_desktop_planner():
    planner = HybridDesktopPlanner()
    planner.register_macro("notepad", [DesktopAction(name="open_notepad")])

    wf1 = DesktopWorkflow(goal="Open notepad and type text")
    planned1 = planner.plan_workflow(wf1)
    assert planned1.state == WorkflowState.EXECUTING
    assert len(planned1.actions) == 1
    assert planned1.actions[0].name == "open_notepad"

    wf2 = DesktopWorkflow(goal="Do something unusual")
    planned2 = planner.plan_workflow(wf2)
    assert planned2.state == WorkflowState.EXECUTING
    assert len(planned2.actions) == 2
