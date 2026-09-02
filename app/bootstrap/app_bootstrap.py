"""
App Startup Bootstrap Lifecycle.
Executable Host -> Splash Screen -> Load Config -> Init Kernel -> Init DI Container -> Init Runtimes -> Connect Backend.

AppBootstrap is a THIN startup coordinator.
It does NOT construct runtime/orchestration objects directly.
All services are resolved from the Kernel's DI Container (single composition root).
"""

import asyncio
from typing import Any, Dict, Optional

from dotenv import load_dotenv


class AppBootstrap:
    """
    App Startup Lifecycle Manager.

    Bootstraps the Kernel (which initializes the DI Container),
    then resolves all required services from the container.
    This ensures a single composition root with no duplicate service instances.
    """

    def __init__(self):
        self.kernel = None
        self.event_bus = None
        self.telemetry = None
        self.negotiator = None
        self.desktop_runtime = None
        self.vision_runtime = None
        self.goal_manager = None
        self.coordinator = None
        self.is_bootstrapped: bool = False

    async def initialize(self) -> Dict[str, Any]:
        """Runs the full startup sequence through Kernel and DI Container."""
        from core.kernel.bootstrap import bootstrap
        from core.events.event_bus import EventBus
        from core.runtime.capability import CapabilityNegotiator
        from core.goals import GoalManager
        from core.cognition import CognitiveCoordinator
        from core.desktop.interfaces import IDesktopRuntime
        from core.vision.interfaces import IVisionRuntime
        from core.telemetry.dashboard import TelemetryDashboard

        # 1. Boot Kernel — this is the ONLY composition root
        self.kernel = bootstrap()

        # 2. Resolve EventBus from Kernel's DI container (shared singleton)
        self.event_bus = self.kernel.event_bus

        # 3. Resolve telemetry (separate, lightweight — not in DI)
        self.telemetry = TelemetryDashboard(self.event_bus)

        # 4. Resolve all runtime/orchestration services from DI container
        container = self.kernel.container
        self.negotiator = container.resolve(CapabilityNegotiator)
        self.desktop_runtime = container.resolve(IDesktopRuntime)
        self.vision_runtime = container.resolve(IVisionRuntime)
        self.goal_manager = container.resolve(GoalManager)
        self.coordinator = container.resolve(CognitiveCoordinator)

        # 5. Start runtimes
        await self.desktop_runtime.start()
        await self.vision_runtime.start()

        # 6. Register runtimes with the CapabilityNegotiator
        self.negotiator.register_runtime("desktop", self.desktop_runtime)
        self.negotiator.register_runtime("vision", self.vision_runtime)

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
