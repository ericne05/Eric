"""
App Startup Bootstrap Lifecycle.
Executable Host -> Splash Screen -> Load Config -> Init RuntimeHost (Kernel + DI + Runtimes) -> Connect Backend.

AppBootstrap is a startup coordinator that delegates backend lifecycle management
to EricRuntimeHost. All services are resolved from the Kernel's DI Container
(single composition root).
"""

from typing import Any, Dict, Optional


class AppBootstrap:
    """
    App Startup Lifecycle Manager.

    Coordinates application bootstrap by delegating to EricRuntimeHost,
    which manages the Kernel, EventBus, runtimes, and orchestration lifecycle.
    """

    def __init__(self, runtime_host: Optional[Any] = None):
        from core.runtime.host import EricRuntimeHost
        self.runtime_host: EricRuntimeHost = runtime_host or EricRuntimeHost()
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
        """Runs the full startup sequence through EricRuntimeHost and DI Container."""
        await self.runtime_host.start()

        # Expose references from runtime_host for backward compatibility with App layer
        self.kernel = self.runtime_host.kernel
        self.event_bus = self.runtime_host.event_bus
        self.negotiator = self.runtime_host.negotiator
        self.desktop_runtime = self.runtime_host.desktop_runtime
        self.vision_runtime = self.runtime_host.vision_runtime
        self.goal_manager = self.runtime_host.goal_manager
        self.coordinator = self.runtime_host.coordinator

        from core.telemetry.dashboard import TelemetryDashboard
        self.telemetry = TelemetryDashboard(self.event_bus)

        self.is_bootstrapped = True
        return {
            "status": "ready",
            "runtimes": ["desktop", "vision"],
            "event_bus": True,
            "telemetry": True,
        }

    async def shutdown(self) -> None:
        """Gracefully shuts down runtimes and Kernel via EricRuntimeHost."""
        if self.runtime_host:
            await self.runtime_host.stop()
        self.is_bootstrapped = False
