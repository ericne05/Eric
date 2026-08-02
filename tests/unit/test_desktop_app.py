"""
Unit Tests for Sprint 17 — Eric Desktop Client (v1.0 Product Release).
"""

import asyncio
import pytest

from app.bootstrap.app_bootstrap import AppBootstrap
from app.services.backend_bridge import BackendBridge
from app.services.session_manager import SessionManager
from app.ui.chat.chat_widget import ChatWidget
from app.ui.notification.notification_center import NotificationCenter
from app.ui.widgets.activity_console import ActivityConsole
from app.ui.widgets.command_palette import CommandPalette
from app.ui.widgets.error_panel import ErrorDiagnosticPanel
from app.ui.widgets.goal_dashboard import GoalDashboardWidget
from app.ui.widgets.runtime_status import RuntimeStatusWidget
from app.viewmodels.main_viewmodel import MainViewModel


@pytest.mark.asyncio
async def test_app_bootstrap_startup_sequence():
    bootstrap = AppBootstrap()
    res = await bootstrap.initialize()
    assert res["status"] == "ready"
    assert bootstrap.is_bootstrapped is True
    assert len(res["runtimes"]) == 2

    await bootstrap.shutdown()
    assert bootstrap.is_bootstrapped is False


def test_session_manager():
    sm = SessionManager()
    session = sm.create_session("Test Session")
    assert session.id is not None
    assert session.title == "Test Session"

    msg = sm.add_message("Hello Eric", sender="user")
    assert msg.content == "Hello Eric"
    assert len(session.messages) == 1

    restored = sm.restore_last_session()
    assert restored.id == session.id


def test_activity_console_and_notifications():
    console = ActivityConsole()
    entry = console.log("System Ready")
    assert "System Ready" in entry
    assert len(console.get_logs()) == 1

    nc = NotificationCenter()
    item = nc.notify("Download", "Started", level="info")
    assert item.title == "Download"
    assert len(nc.get_unread()) == 1


def test_command_palette():
    cp = CommandPalette()
    results = cp.search("Settings")
    assert "Open Settings" in results

    res = cp.execute_command("Open Settings")
    assert res == "Opened Settings"


def test_error_diagnostic_panel():
    panel = ErrorDiagnosticPanel()
    step = panel.record_step("Selector not found", status="failed", details="CSS #btn missing")
    assert step.status == "failed"
    assert len(panel.get_trace()) == 1


@pytest.mark.asyncio
async def test_main_viewmodel_and_widgets():
    bootstrap = AppBootstrap()
    await bootstrap.initialize()

    sm = SessionManager()
    bridge = BackendBridge(bootstrap, sm)
    vm = MainViewModel(bridge)

    chat_widget = ChatWidget()
    runtime_status = RuntimeStatusWidget()
    goal_dashboard = GoalDashboardWidget()

    msg = await vm.submit_prompt("Run desktop workflow")
    assert msg is not None
    assert vm.current_status == "Completed"
    assert vm.goal_progress == 100.0

    chat_widget.update_messages(vm.get_messages())
    rendered = chat_widget.get_rendered_messages()
    assert len(rendered) >= 2

    badges = runtime_status.get_badges()
    assert "desktop" in badges

    goal_dashboard.update_progress(vm.goal_progress, 4, 4, vm.current_status)
    summary = goal_dashboard.get_dashboard_summary()
    assert summary["progress_percentage"] == 100.0

    await bootstrap.shutdown()
