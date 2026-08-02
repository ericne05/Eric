"""
Integration Test — Sprint 17: Desktop Client End-to-End Pipeline.
Tests full lifecycle: Desktop Client Launch -> Session Restore -> User Prompt -> Activity Console Log -> Cognitive Coordinator -> Goal Completion -> Notification.
"""

import asyncio
import pytest

from app.main import EricDesktopClient


@pytest.mark.asyncio
async def test_full_desktop_client_e2e_pipeline():
    client = EricDesktopClient()

    # 1. Launch Client App
    launch_res = await client.launch()
    assert launch_res["status"] == "online"
    assert client.is_running is True

    # 2. User Prompt
    reply = await client.send_prompt("Open Chrome, login to portal, download report")
    assert reply is not None
    assert "✓ Completed goal" in reply

    # 3. Check Session Manager & History
    session = client.session_manager.get_active_session()
    assert len(session.messages) >= 2

    # 4. Check Activity Console Logs
    logs = client.activity_console.get_logs()
    assert len(logs) > 0
    assert any("User Input" in log for log in logs)

    # 5. Check In-App Notification Center
    unread = client.notification_center.get_unread()
    assert len(unread) > 0
    assert unread[-1].title == "Goal Completed"

    # 6. Shutdown Client
    await client.shutdown()
    assert client.is_running is False
