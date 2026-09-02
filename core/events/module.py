"""
EventBus Module Registration for DI Container.

Registers EventBus as a singleton service.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class EventBusModule(IDependencyModule):
    """
    Registers the EventBus into the DI Container as a singleton.

    Usage::

        EventBusModule().register(container)
    """

    def register(self, container: "Container") -> None:
        from core.events import EventBus

        container.add_singleton(EventBus, EventBus)
