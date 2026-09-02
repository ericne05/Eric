"""
Comprehensive Unit Tests for Sprint 12.5 — Native Windows Integration.
"""

import asyncio
import pytest

from core.desktop import (
    ActionPolicy,
    AdapterHealthState,
    DesktopAction,
    DesktopActionQueue,
    DesktopActionResult,
    EmergencyStopManager,
    ExponentialRetry,
    FixedRetry,
    LinearRetry,
    MockDesktopAdapter,
    WindowsDesktopAdapter,
)
from core.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_windows_adapter_sandbox_and_capabilities():
    event_bus = EventBus()
    events = []
    event_bus.subscribe("desktop.action.started", lambda e: events.append(e))

    # Enable sandbox=True for unit test safety
    adapter = WindowsDesktopAdapter(event_bus=event_bus, sandbox=True)
    await adapter.start()

    res_click = await adapter.ui.click(300, 400)
    assert res_click.success is True
    assert res_click.data["dry_run"] is True

    res_type = await adapter.ui.type_text("Hello Windows 11")
    assert res_type.success is True
    assert res_type.data["dry_run"] is True

    caps = adapter.get_capabilities()
    assert caps.can_mouse is True
    assert caps.can_keyboard is True
    assert caps.can_ocr is False  # Decoupled to Vision Runtime

    health = adapter.check_health()
    assert health.state == AdapterHealthState.HEALTHY

    await adapter.stop()
    assert len(events) == 2


@pytest.mark.asyncio
async def test_emergency_stop_manager():
    event_bus = EventBus()
    stopped_events = []
    event_bus.subscribe("desktop.emergency_stop", lambda e: stopped_events.append(e))

    manager = EmergencyStopManager(event_bus=event_bus)
    assert manager.is_stopped is False

    cb_triggered = []
    manager.register_stop_callback(lambda: cb_triggered.append(True))

    await manager.trigger_emergency_stop(reason="Corner mouse failsafe")
    assert manager.is_stopped is True
    assert len(cb_triggered) == 1
    assert len(stopped_events) == 1
    assert stopped_events[0].payload["reason"] == "Corner mouse failsafe"


def test_retry_strategies():
    fixed = FixedRetry()
    linear = LinearRetry()
    expo = ExponentialRetry()

    assert fixed.calculate_delay_seconds(1) == 1.0
    assert fixed.calculate_delay_seconds(3) == 1.0

    assert linear.calculate_delay_seconds(1) == 1.0
    assert linear.calculate_delay_seconds(3) == 3.0

    assert expo.calculate_delay_seconds(1) == 1.0
    assert expo.calculate_delay_seconds(2) == 2.0
    assert expo.calculate_delay_seconds(3) == 4.0


@pytest.mark.asyncio
async def test_transactional_rollback():
    queue = DesktopActionQueue()

    act_a = DesktopAction(id="a", name="create_file", status="completed", inverse_action=DesktopAction(id="inv_a", name="delete_file"))
    act_b = DesktopAction(id="b", name="write_data", status="completed", inverse_action=DesktopAction(id="inv_b", name="clear_data"))
    act_c = DesktopAction(id="c", name="invalid_action", status="failed")

    txn = queue.create_transaction("txn1", [act_a, act_b, act_c])
    assert txn.status == "pending"

    executed_inverses = []

    async def mock_executor(inv_action):
        executed_inverses.append(inv_action.name)
        return DesktopActionResult(success=True)

    results = await queue.rollback_transaction("txn1", mock_executor)
    assert len(results) == 2
    # Rollback order must be reverse: B then A
    assert executed_inverses == ["clear_data", "delete_file"]
    assert txn.status == "rolled_back"


def test_parallel_ready_actions():
    queue = DesktopActionQueue()

    act1 = DesktopAction(id="1", name="open_notepad", priority=1)
    act2 = DesktopAction(id="2", name="open_calc", priority=2)
    act3 = DesktopAction(id="3", name="merge_windows", dependencies=["1", "2"])

    queue.add_action(act1)
    queue.add_action(act2)
    queue.add_action(act3)

    ready = queue.get_parallel_ready_actions()
    assert len(ready) == 2
    # Highest priority first
    assert ready[0].id == "2"
    assert ready[1].id == "1"


def test_action_policy_handling():
    queue = DesktopActionQueue()

    act1 = DesktopAction(id="1", name="click_missing", policy=ActionPolicy.IGNORE)
    act2 = DesktopAction(id="2", name="subsequent_task", dependencies=["1"])

    queue.add_action(act1)
    queue.add_action(act2)

    cancelled = queue.mark_failed("1")
    # ActionPolicy.IGNORE should not cancel dependent actions
    assert len(cancelled) == 0
