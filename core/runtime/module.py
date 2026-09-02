"""
Runtime System DI Module.

Registers all runtime adapters, CapabilityNegotiator, GoalManager, and
CognitiveCoordinator in the DI Container so that AppBootstrap can resolve
them rather than constructing them manually.

Architecture:
    Kernel.boot()
        → RuntimeModule.register(container)
            → EventBus (shared from container)
            → CapabilityNegotiator
            → DesktopRuntime (WindowsDesktopAdapter on win32, MockDesktopAdapter otherwise)
            → VisionRuntime (MockVisionAdapter)
            → GoalManager
            → CognitiveCoordinator

All instances are singletons and share the SAME EventBus already in the container.
"""

import sys
from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class RuntimeModule(IDependencyModule):
    """
    Registers the Runtime + Orchestration layer in the DI Container.

    Components registered:
    - CapabilityNegotiator  (singleton)
    - DesktopRuntime        (singleton, platform-selected)
    - VisionRuntime         (singleton)
    - GoalManager           (singleton)
    - CognitiveCoordinator  (singleton)
    """

    def register(self, container: "Container") -> None:
        from core.events.event_bus import EventBus
        from core.runtime.capability import CapabilityNegotiator
        from core.goals import GoalManager
        from core.cognition import CognitiveCoordinator

        # CapabilityNegotiator — singleton, no dependencies
        container.add_singleton(CapabilityNegotiator, CapabilityNegotiator)

        # DesktopRuntime — platform-selected
        def _desktop_factory(c):
            bus = c.resolve(EventBus)
            if sys.platform == "win32":
                from core.desktop import WindowsDesktopAdapter
                return WindowsDesktopAdapter(event_bus=bus)
            else:
                from core.desktop import MockDesktopAdapter
                return MockDesktopAdapter(event_bus=bus)

        from core.desktop.interfaces import IDesktopRuntime
        container.add_singleton(IDesktopRuntime, _desktop_factory)

        # VisionRuntime
        def _vision_factory(c):
            from core.vision import MockVisionAdapter
            return MockVisionAdapter()

        from core.vision.interfaces import IVisionRuntime
        container.add_singleton(IVisionRuntime, _vision_factory)

        # GoalManager — needs CapabilityNegotiator + EventBus
        def _goal_manager_factory(c):
            return GoalManager(
                negotiator=c.resolve(CapabilityNegotiator),
                event_bus=c.resolve(EventBus),
            )

        container.add_singleton(GoalManager, _goal_manager_factory)

        # CognitiveCoordinator — needs CapabilityNegotiator
        def _coordinator_factory(c):
            return CognitiveCoordinator(
                negotiator=c.resolve(CapabilityNegotiator),
            )

        container.add_singleton(CognitiveCoordinator, _coordinator_factory)
