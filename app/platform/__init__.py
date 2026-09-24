"""
Platform Abstractions Package (app/platform).

Exports protocols and platform implementations for:
- Single instance enforcement
- Desktop system tray management
- Presentation host visibility
- Autostart / Windows startup management
"""

from app.platform.interfaces import (
    IPresentationHost,
    ISingleInstanceLock,
    IStartupManager,
    ITrayManager,
)
from app.platform.presentation import MockPresentationHost
from app.platform.single_instance import (
    FileSingleInstanceLock,
    MockSingleInstanceLock,
    WindowsSingleInstanceLock,
)
from app.platform.startup import (
    MockStartupManager,
    WindowsStartupManager,
)
from app.platform.tray import (
    MockTrayManager,
    PystrayTrayManager,
)

__all__ = [
    "ISingleInstanceLock",
    "ITrayManager",
    "IPresentationHost",
    "IStartupManager",
    "WindowsSingleInstanceLock",
    "FileSingleInstanceLock",
    "MockSingleInstanceLock",
    "PystrayTrayManager",
    "MockTrayManager",
    "MockPresentationHost",
    "WindowsStartupManager",
    "MockStartupManager",
]
