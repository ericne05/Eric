"""
Transport-Agnostic Client / Runtime Interface (IEricRuntime).

Defines the boundary between client applications (Desktop UI, CLI, future MCP/Voice)
and the Eric Runtime Host.

Clients communicate exclusively through this interface. No internal Kernel,
DI Container, EventBus, or live execution engine instances are exposed.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Optional, Union

from core.runtime.models import RuntimeEvent, RuntimeSnapshot, RuntimeStatus

# Listener signature: sync or async callable accepting a RuntimeEvent
RuntimeEventListener = Callable[[RuntimeEvent], Union[None, Coroutine[Any, Any, None]]]


class IEricRuntime(ABC):
    """
    Public contract for interacting with the Eric Runtime.

    Enables completely transport-agnostic execution: in-process direct calls,
    named pipes, local domain sockets, or remote protocols.
    """

    @abstractmethod
    def get_status(self) -> RuntimeStatus:
        """Return the current high-level runtime lifecycle status."""
        pass

    @abstractmethod
    def get_snapshot(self) -> RuntimeSnapshot:
        """
        Return a serializable, snapshot of the runtime's current state.

        Guaranteed to contain no live Python service objects.
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        Start the runtime host and underlying services.

        Transitions: CREATED -> STARTING -> READY (or ERROR).
        Emits 'runtime.starting' and 'runtime.ready' (or 'runtime.error').
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully stop the runtime host and underlying services.

        Transitions: READY/ERROR -> STOPPING -> STOPPED.
        Emits 'runtime.stopping' and 'runtime.stopped'.
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: str, handler: RuntimeEventListener) -> None:
        """
        Subscribe a listener to structured runtime events.

        Args:
            event_type: Event type name (e.g. 'runtime.ready', 'runtime.error') or '*' for all.
            handler: Callable accepting a RuntimeEvent (sync or coroutine).
        """
        pass

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: RuntimeEventListener) -> None:
        """
        Unsubscribe a listener from runtime events.

        Args:
            event_type: Event type name or '*'.
            handler: The previously subscribed callable.
        """
        pass
