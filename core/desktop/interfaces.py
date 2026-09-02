"""
Desktop Runtime Interfaces (Sprint 12.5 Product-Grade).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from core.desktop.models import (
    AdapterHealth,
    DesktopActionResult,
    RuntimeCapabilityRegistry,
    WindowInfo,
)


class IDesktopUI(ABC):
    """Interface for desktop mouse and keyboard UI interactions."""

    @abstractmethod
    async def click(self, x: int, y: int, timeout_ms: int = 10000) -> DesktopActionResult:
        pass

    @abstractmethod
    async def double_click(self, x: int, y: int, timeout_ms: int = 10000) -> DesktopActionResult:
        pass

    @abstractmethod
    async def right_click(self, x: int, y: int, timeout_ms: int = 10000) -> DesktopActionResult:
        pass

    @abstractmethod
    async def type_text(self, text: str, delay_ms: int = 50) -> DesktopActionResult:
        pass

    @abstractmethod
    async def hotkey(self, *keys: str) -> DesktopActionResult:
        pass

    @abstractmethod
    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> DesktopActionResult:
        pass


class IDesktopScreenshot(ABC):
    """Interface for desktop screen capturing."""

    @abstractmethod
    async def capture_screen(self) -> DesktopActionResult:
        pass

    @abstractmethod
    async def capture_window(self, window_id: str) -> DesktopActionResult:
        pass


class IWindowManager(ABC):
    """Interface for desktop window management."""

    @abstractmethod
    async def get_active_windows(self) -> List[WindowInfo]:
        pass

    @abstractmethod
    async def get_focused_window(self) -> Optional[WindowInfo]:
        pass

    @abstractmethod
    async def focus_window(self, window_id: str) -> bool:
        pass

    @abstractmethod
    async def close_window(self, window_id: str) -> bool:
        pass


class IDesktopClipboard(ABC):
    """Interface for managing OS Clipboard."""

    @abstractmethod
    async def get_text(self) -> str:
        pass

    @abstractmethod
    async def set_text(self, text: str) -> bool:
        pass


class IDesktopNotification(ABC):
    """Interface for OS Native Notifications."""

    @abstractmethod
    async def send_notification(self, title: str, message: str) -> bool:
        pass


class IDesktopSystem(ABC):
    """Interface for OS Power and System Control."""

    @abstractmethod
    async def lock_screen(self) -> bool:
        pass

    @abstractmethod
    async def set_volume(self, level_percent: int) -> bool:
        pass


class IDesktopRuntime(ABC):
    """Main interface for controlling the desktop automation lifecycle."""

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @property
    @abstractmethod
    def ui(self) -> IDesktopUI:
        pass

    @property
    @abstractmethod
    def screenshot(self) -> IDesktopScreenshot:
        pass

    @property
    @abstractmethod
    def window_manager(self) -> IWindowManager:
        pass

    @property
    @abstractmethod
    def clipboard(self) -> IDesktopClipboard:
        pass

    @property
    @abstractmethod
    def notification(self) -> IDesktopNotification:
        pass

    @property
    @abstractmethod
    def system(self) -> IDesktopSystem:
        pass

    @abstractmethod
    def get_capabilities(self) -> RuntimeCapabilityRegistry:
        pass

    @abstractmethod
    def check_health(self) -> AdapterHealth:
        pass
