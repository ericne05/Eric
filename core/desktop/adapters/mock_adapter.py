"""
Mock Desktop Adapter Implementation (Updated for Sprint 12.5).
"""

from typing import List, Optional

from core.desktop.enums import AdapterHealthState, DesktopState
from core.desktop.interfaces import (
    IDesktopClipboard,
    IDesktopNotification,
    IDesktopRuntime,
    IDesktopScreenshot,
    IDesktopSystem,
    IDesktopUI,
    IWindowManager,
)
from core.desktop.models import AdapterHealth, DesktopActionResult, RuntimeCapabilityRegistry, WindowInfo
from core.events.event import Event
from core.events.event_bus import EventBus


class MockDesktopUI(IDesktopUI):
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus

    async def _emit(self, name: str, payload: dict):
        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    name=name,
                    source="desktop.ui",
                    payload=payload,
                )
            )

    async def click(self, x: int, y: int, timeout_ms: int = 10000) -> DesktopActionResult:
        await self._emit("desktop.action.started", {"action": "click", "x": x, "y": y})
        result = DesktopActionResult(success=True, data={"x": x, "y": y, "action": "click"})
        await self._emit("desktop.action.completed", {"action": "click", "result": result})
        return result

    async def double_click(self, x: int, y: int, timeout_ms: int = 10000) -> DesktopActionResult:
        await self._emit("desktop.action.started", {"action": "double_click", "x": x, "y": y})
        result = DesktopActionResult(success=True, data={"x": x, "y": y, "action": "double_click"})
        await self._emit("desktop.action.completed", {"action": "double_click", "result": result})
        return result

    async def right_click(self, x: int, y: int, timeout_ms: int = 10000) -> DesktopActionResult:
        await self._emit("desktop.action.started", {"action": "right_click", "x": x, "y": y})
        result = DesktopActionResult(success=True, data={"x": x, "y": y, "action": "right_click"})
        await self._emit("desktop.action.completed", {"action": "right_click", "result": result})
        return result

    async def type_text(self, text: str, delay_ms: int = 50) -> DesktopActionResult:
        await self._emit("desktop.action.started", {"action": "type_text", "text": text})
        result = DesktopActionResult(success=True, data={"text": text, "action": "type_text"})
        await self._emit("desktop.action.completed", {"action": "type_text", "result": result})
        return result

    async def hotkey(self, *keys: str) -> DesktopActionResult:
        await self._emit("desktop.action.started", {"action": "hotkey", "keys": list(keys)})
        result = DesktopActionResult(success=True, data={"keys": list(keys), "action": "hotkey"})
        await self._emit("desktop.action.completed", {"action": "hotkey", "result": result})
        return result

    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> DesktopActionResult:
        await self._emit("desktop.action.started", {"action": "drag", "from": (start_x, start_y), "to": (end_x, end_y)})
        result = DesktopActionResult(success=True, data={"from": (start_x, start_y), "to": (end_x, end_y)})
        await self._emit("desktop.action.completed", {"action": "drag", "result": result})
        return result


class MockDesktopScreenshot(IDesktopScreenshot):
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus

    async def capture_screen(self) -> DesktopActionResult:
        return DesktopActionResult(
            success=True,
            screenshot_base64="mock_base64_fullscreen",
            data={"resolution": (1920, 1080)},
        )

    async def capture_window(self, window_id: str) -> DesktopActionResult:
        return DesktopActionResult(
            success=True,
            screenshot_base64=f"mock_base64_window_{window_id}",
            data={"window_id": window_id},
        )


class MockWindowManager(IWindowManager):
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._windows = [
            WindowInfo(id="w1", title="Notepad", process_name="notepad.exe", process_id=101, is_focused=True),
            WindowInfo(id="w2", title="File Explorer", process_name="explorer.exe", process_id=102, is_focused=False),
        ]

    async def get_active_windows(self) -> List[WindowInfo]:
        return self._windows

    async def get_focused_window(self) -> Optional[WindowInfo]:
        for w in self._windows:
            if w.is_focused:
                return w
        return None

    async def focus_window(self, window_id: str) -> bool:
        found = False
        for w in self._windows:
            if w.id == window_id:
                w.is_focused = True
                found = True
            else:
                w.is_focused = False
        return found

    async def close_window(self, window_id: str) -> bool:
        initial_len = len(self._windows)
        self._windows = [w for w in self._windows if w.id != window_id]
        return len(self._windows) < initial_len


class MockDesktopClipboard(IDesktopClipboard):
    def __init__(self):
        self._content = "Mock Clipboard Content"

    async def get_text(self) -> str:
        return self._content

    async def set_text(self, text: str) -> bool:
        self._content = text
        return True


class MockDesktopNotification(IDesktopNotification):
    async def send_notification(self, title: str, message: str) -> bool:
        return True


class MockDesktopSystem(IDesktopSystem):
    async def lock_screen(self) -> bool:
        return True

    async def set_volume(self, level_percent: int) -> bool:
        return True


class MockDesktopAdapter(IDesktopRuntime):
    """Mock implementation of the Desktop Runtime."""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._state = DesktopState.STOPPED
        self._ui = MockDesktopUI(event_bus)
        self._screenshot = MockDesktopScreenshot(event_bus)
        self._window_manager = MockWindowManager(event_bus)
        self._clipboard = MockDesktopClipboard()
        self._notification = MockDesktopNotification()
        self._system = MockDesktopSystem()

    async def start(self) -> None:
        self._state = DesktopState.READY
        if self._event_bus:
            await self._event_bus.publish(Event(name="desktop.state.changed", source="desktop", payload={"state": self._state.value}))

    async def stop(self) -> None:
        self._state = DesktopState.STOPPED
        if self._event_bus:
            await self._event_bus.publish(Event(name="desktop.state.changed", source="desktop", payload={"state": self._state.value}))

    @property
    def ui(self) -> IDesktopUI:
        return self._ui

    @property
    def screenshot(self) -> IDesktopScreenshot:
        return self._screenshot

    @property
    def window_manager(self) -> IWindowManager:
        return self._window_manager

    @property
    def clipboard(self) -> IDesktopClipboard:
        return self._clipboard

    @property
    def notification(self) -> IDesktopNotification:
        return self._notification

    @property
    def system(self) -> IDesktopSystem:
        return self._system

    def get_capabilities(self) -> RuntimeCapabilityRegistry:
        return RuntimeCapabilityRegistry(
            can_mouse=True,
            can_keyboard=True,
            can_window=True,
            can_screenshot=True,
            can_clipboard=True,
            can_notification=True,
            can_system_power=True,
            can_ocr=False,
            can_voice=False,
        )

    def check_health(self) -> AdapterHealth:
        return AdapterHealth(state=AdapterHealthState.HEALTHY)
