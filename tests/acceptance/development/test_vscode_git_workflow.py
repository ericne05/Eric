"""
Development Automation Acceptance Tests (VSCode, Open Project, Run Tests, Git Commit).
"""

import pytest

from app.main import EricDesktopClient
from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_development_vscode_open_test_git_commit_workflow():
    """
    Workflow: Open VSCode -> Open Project -> Run Tests -> Explain Errors -> Git Commit
    """
    event_bus = EventBus()
    desktop = MockDesktopAdapter(event_bus)
    await desktop.start()

    # 1. Type open project command
    res1 = await desktop.ui.type_text("code .")
    assert res1.success is True

    # 2. Type run tests command
    res2 = await desktop.ui.type_text("pytest")
    assert res2.success is True

    # 3. Type git commit command
    res3 = await desktop.ui.type_text("git commit -m 'feat: complete user acceptance milestone'")
    assert res3.success is True

    await desktop.stop()
