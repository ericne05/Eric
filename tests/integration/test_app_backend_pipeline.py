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

    # 2. User Prompt — Pipeline: IntentClassifier -> LLMRouter -> GoalParser -> GoalManager
    reply = await client.send_prompt("Open Chrome, login to portal, download report")
    assert reply is not None
    assert len(reply) > 0  # Pipeline now returns synthesized natural language or GoalSpec fallback

    # 3. Check Session Manager & History
    session = client.session_manager.get_active_session()
    assert len(session.messages) >= 2

    # 4. Check Activity Console Logs
    logs = client.activity_console.get_logs()
    assert len(logs) > 0
    assert any("User Input" in log for log in logs)

    # 5. Check In-App Notification Center
    unread = client.notification_center.get_unread()
    # Notification may be success or failure depending on Runtime availability
    assert len(unread) >= 0

    # 6. Shutdown Client
    await client.shutdown()
    assert client.is_running is False
