"""
Event definition for Eric Event Bus.

Implements the standardized Event dataclass per the Eric Development Constitution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from core.events.exceptions import InvalidEventError


@dataclass(frozen=True)
class Event:
    """
    Standardized immutable Event object transmitted via EventBus.

    Attributes:
        id: Unique UUID for this event instance.
        name: Event name using pattern [namespace].[component].[action] or [namespace].[action].
        source: Module or component emitting the event.
        timestamp: Time of event creation (UTC).
        correlation_id: Optional UUID to correlate related events for tracing.
        payload: Event payload dictionary.
        metadata: Optional metadata dictionary.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    source: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate event attributes after initialization."""
        if not self.name or not isinstance(self.name, str):
            raise InvalidEventError("Event 'name' must be a non-empty string.")
        if not self.source or not isinstance(self.source, str):
            raise InvalidEventError("Event 'source' must be a non-empty string.")
        if "." not in self.name:
            raise InvalidEventError(
                f"Event name '{self.name}' must follow format [namespace].[component].[action]."
            )

    @classmethod
    def create(
        cls,
        name: str,
        source: str,
        payload: dict[str, Any] | None = None,
        correlation_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Event":
        """
        Factory helper to create a new Event instance.

        Args:
            name: Event name following [namespace].[component].[action].
            source: Source module or component name.
            payload: Optional dictionary payload.
            correlation_id: Optional correlation UUID for event tracing.
            metadata: Optional metadata dictionary.

        Returns:
            An immutable Event instance.
        """
        return cls(
            name=name,
            source=source,
            correlation_id=correlation_id,
            payload=payload if payload is not None else {},
            metadata=metadata if metadata is not None else {},
        )
