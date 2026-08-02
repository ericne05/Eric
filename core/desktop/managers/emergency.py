"""
Emergency Stop Manager for Desktop Runtime (Sprint 12.5 Product-Grade).
"""

from typing import Callable, List, Optional
from core.events.event import Event
from core.events.event_bus import EventBus


class EmergencyStopManager:
    """
    Emergency Stop Manager supporting Failsafe triggers, keyboard shortcuts,
    and voice commands to immediately abort all running actions.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._is_stopped = False
        self._callbacks: List[Callable[[], None]] = []

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    def register_stop_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    async def trigger_emergency_stop(self, reason: str = "User requested Emergency Stop") -> None:
        """Triggers an immediate emergency stop asynchronously."""
        self._is_stopped = True
        
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

        if self._event_bus:
            await self._event_bus.publish(
                Event(
                    name="desktop.emergency_stop",
                    source="emergency_manager",
                    payload={"reason": reason},
                )
            )

    def reset(self) -> None:
        self._is_stopped = False
