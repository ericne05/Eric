"""
App Startup Bootstrap Lifecycle.
Executable Host -> Splash Screen -> Load Config -> Init Kernel -> Init DI Container -> Init Runtimes -> Connect Backend.
"""

import asyncio
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from core.cognition import CognitiveCoordinator
from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.goals import GoalManager
from core.runtime.capability import CapabilityNegotiator
from core.telemetry.dashboard import TelemetryDashboard
from core.vision import MockVisionAdapter


class AppBootstrap:
    """
    App Startup Lifecycle Manager.
    Bootstraps Kernel, EventBus, Runtimes, GoalManager, and CognitiveCoordinator.
    """

    def __init__(self):
        self.event_bus: Optional[EventBus] = None
        self.telemetry: Optional[TelemetryDashboard] = None
        self.negotiator: Optional[CapabilityNegotiator] = None
        self.desktop_runtime: Optional[MockDesktopAdapter] = None
        self.vision_runtime: Optional[MockVisionAdapter] = None
        self.goal_manager: Optional[GoalManager] = None
        self.coordinator: Optional[CognitiveCoordinator] = None
        self.is_bootstrapped: bool = False

    async def initialize(self) -> Dict[str, Any]:
        """Runs the full startup sequence."""
        load_dotenv()
        self.event_bus = EventBus()
        self.telemetry = TelemetryDashboard(self.event_bus)

        self.negotiator = CapabilityNegotiator()
        self.desktop_runtime = MockDesktopAdapter(self.event_bus)
        self.vision_runtime = MockVisionAdapter()

        await self.desktop_runtime.start()
        await self.vision_runtime.start()

        self.negotiator.register_runtime("desktop", self.desktop_runtime)
        self.negotiator.register_runtime("vision", self.vision_runtime)

        self.goal_manager = GoalManager(negotiator=self.negotiator, event_bus=self.event_bus)
        self.coordinator = CognitiveCoordinator(negotiator=self.negotiator)

        self.is_bootstrapped = True
        return {
            "status": "ready",
            "runtimes": ["desktop", "vision"],
            "event_bus": True,
            "telemetry": True,
        }

    async def shutdown(self) -> None:
        if self.desktop_runtime and hasattr(self.desktop_runtime, "stop"):
            await self.desktop_runtime.stop()
        if self.vision_runtime and hasattr(self.vision_runtime, "stop"):
            await self.vision_runtime.stop()
        self.is_bootstrapped = False
