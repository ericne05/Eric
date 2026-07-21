"""
Custom exceptions for the Event Bus module in Eric.
"""


class EventBusError(Exception):
    """Base exception for all Event Bus errors."""

    pass


class InvalidEventError(EventBusError):
    """Raised when an event structure or payload is invalid."""

    pass
