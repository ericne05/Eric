"""
Event Bus implementation for Eric.

Provides asynchronous and synchronous event publishing and subscription
with pattern matching and exception isolation.
"""

import asyncio
import fnmatch
import inspect
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from core.events.event import Event
from core.events.exceptions import EventBusError

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Any]


class EventBus:
    """
    Central event bus orchestrating asynchronous Pub/Sub messaging.

    Supports exact event name subscriptions, wildcard patterns (e.g., "system.*", "*"),
    and exception isolation across handlers.
    """

    def __init__(self, enable_history: bool = True, history_limit: int = 100) -> None:
        """
        Initialize the EventBus.

        Args:
            enable_history: Whether to maintain a list of recently published events.
            history_limit: Maximum number of events to retain in history.
        """
        # Map pattern -> list of handlers
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._enable_history = enable_history
        self._history_limit = history_limit
        self._history: list[Event] = []

    # ── Public Methods ────────────────────────────────────

    def subscribe(self, pattern: str, handler: EventHandler) -> None:
        """
        Subscribe a handler function to events matching a pattern.

        Args:
            pattern: Event pattern (e.g., "system.ready", "system.*", "*").
            handler: Callable (sync or async) taking an Event argument.

        Raises:
            EventBusError: If pattern is invalid or handler is not callable.
        """
        if not pattern or not isinstance(pattern, str):
            raise EventBusError("Subscription pattern must be a non-empty string.")
        if not callable(handler):
            raise EventBusError("Handler must be a callable.")

        if handler not in self._subscribers[pattern]:
            self._subscribers[pattern].append(handler)
            logger.debug("Subscribed %r to pattern '%s'", handler, pattern)

    def unsubscribe(self, pattern: str, handler: EventHandler) -> None:
        """
        Unsubscribe a handler function from a pattern.

        Args:
            pattern: Event pattern previously subscribed to.
            handler: Registered handler function.
        """
        if pattern in self._subscribers and handler in self._subscribers[pattern]:
            self._subscribers[pattern].remove(handler)
            if not self._subscribers[pattern]:
                del self._subscribers[pattern]
            logger.debug("Unsubscribed %r from pattern '%s'", handler, pattern)

    async def publish(self, event: Event) -> None:
        """
        Publish an event asynchronously to all matching handlers.

        Args:
            event: Event object to dispatch.
        """
        if not isinstance(event, Event):
            raise EventBusError(f"Expected Event instance, got {type(event).__name__}")

        if self._enable_history:
            self._record_history(event)

        matching_handlers = self._get_matching_handlers(event.name)
        if not matching_handlers:
            logger.debug("No handlers matched event '%s'", event.name)
            return

        for handler in matching_handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as err:
                logger.error(
                    "Error executing handler %r for event '%s': %s",
                    handler,
                    event.name,
                    err,
                    exc_info=True,
                )

    def publish_sync(self, event: Event) -> None:
        """
        Synchronously publish an event (helper for non-async callers).

        Args:
            event: Event object to dispatch.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Schedule task in running event loop
            loop.create_task(self.publish(event))
        else:
            asyncio.run(self.publish(event))

    def has_subscribers(self, event_name: str) -> bool:
        """Check if any subscribers match the given event name."""
        return len(self._get_matching_handlers(event_name)) > 0

    def clear(self) -> None:
        """Remove all subscribers and clear event history."""
        self._subscribers.clear()
        self._history.clear()

    def shutdown(self) -> None:
        """Shut down the EventBus, clearing all subscribers."""
        self.clear()
        logger.info("[EventBus] Event bus shut down.")

    # ── Properties ───────────────────────────────────────

    @property
    def history(self) -> list[Event]:
        """Return a copy of recent published events."""
        return list(self._history)

    # ── Internal Helpers ─────────────────────────────────

    def _get_matching_handlers(self, event_name: str) -> list[EventHandler]:
        """Find all handlers matching the event name."""
        matching: list[EventHandler] = []
        for pattern, handlers in self._subscribers.items():
            if fnmatch.fnmatch(event_name, pattern):
                for h in handlers:
                    if h not in matching:
                        matching.append(h)
        return matching

    def _record_history(self, event: Event) -> None:
        """Append event to history, maintaining limit."""
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history.pop(0)
