"""
Eric Event Bus module.

Provides standardized events, exceptions, and the Pub/Sub EventBus.
"""

from core.events.event import Event
from core.events.event_bus import EventBus, EventHandler
from core.events.exceptions import EventBusError, InvalidEventError

__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "EventBusError",
    "InvalidEventError",
]
