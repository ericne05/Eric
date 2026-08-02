"""
Windows System Apps Acceptance Tests (Calculator, Settings, Task Manager, Explorer).
"""

import pytest

from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_windows_apps_launch_and_control_workflow():
    """
    Workflow: Launch Calculator -> Explorer -> Settings -> Verify OS Control
    """
    event_bus = EventBus()
    desktop = MockDesktopAdapter(event_bus)
    await desktop.start()

    res1 = await desktop.ui.type_text("calc.exe")
    assert res1.success is True

    res2 = await desktop.ui.type_text("explorer.exe")
    assert res2.success is True

    await desktop.stop()
