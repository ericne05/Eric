"""
Dependency Injection Interfaces.

Defines the contracts for module registration and service lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.di.container import Container


class IDependencyModule(ABC):
    """
    Contract for subsystem module registration.

    Each subsystem (logger, events, config, etc.) implements this interface
    to encapsulate its own DI registrations. Kernel only needs to call:

        module.register(container)

    This keeps registration logic co-located with each subsystem,
    preventing a centralized registration file from growing unbounded.
    """

    @abstractmethod
    def register(self, container: "Container") -> None:
        """Register this module's services into the container."""


class ILifecycleAware(ABC):
    """
    Contract for services that need explicit lifecycle management.

    Services implementing this interface will have:
    - initialize() called after construction (on first resolve for singletons).
    - dispose() called during container/scope shutdown.

    Lifecycle order is guaranteed:
        initialize() → [usage] → dispose()

    Examples: BrowserService, VoiceEngine, Scheduler, DatabaseConnection.
    """

    def initialize(self) -> None:
        """
        Called after the service instance is constructed.

        Use for async-unfriendly startup tasks, resource acquisition,
        or establishing connections.
        """

    def dispose(self) -> None:
        """
        Called during container or scope shutdown.

        Use for releasing resources, closing connections, flushing buffers.
        """
