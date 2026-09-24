"""
Platform Interfaces for Windows Companion Lifecycle (app/platform/interfaces.py).

Defines transport- and platform-agnostic protocols:
- ISingleInstanceLock: Process-level single instance ownership.
- ITrayManager: Background system tray lifecycle and status integration.
- IPresentationHost: UI visibility abstraction (show/hide/close separation).
- IStartupManager: Windows autostart configuration abstraction.
"""

from typing import Callable, Optional, Protocol, runtime_checkable

from core.runtime.models import RuntimeStatus


@runtime_checkable
class ISingleInstanceLock(Protocol):
    """Protocol for single-instance application ownership."""

    def acquire(self) -> bool:
        """Attempt to acquire single-instance ownership. Returns True if acquired, False if already running."""
        ...

    def release(self) -> None:
        """Release the acquired single-instance lock."""
        ...

    @property
    def is_locked(self) -> bool:
        """Check if lock is currently held by this process."""
        ...


@runtime_checkable
class ITrayManager(Protocol):
    """Protocol for desktop system tray management."""

    def start(self) -> None:
        """Start the background system tray icon."""
        ...

    def stop(self) -> None:
        """Stop and remove the system tray icon."""
        ...

    def set_status(self, status: RuntimeStatus) -> None:
        """Update tray status display based on authoritative RuntimeStatus."""
        ...

    def is_running(self) -> bool:
        """Check if tray icon is active."""
        ...

    def set_callbacks(
        self,
        on_open: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        """Configure callbacks for tray actions ('Open Eric' and 'Quit Eric')."""
        ...


@runtime_checkable
class IPresentationHost(Protocol):
    """
    Protocol for client presentation hosts (CLI, desktop shell, future Stitch UI).

    Enforces the fundamental distinction between hiding UI vs quitting the application.
    """

    def show(self) -> None:
        """Display the presentation window/surface."""
        ...

    def hide(self) -> None:
        """Hide the presentation window/surface without terminating backend runtime."""
        ...

    def is_visible(self) -> bool:
        """Check if presentation surface is currently visible."""
        ...


@runtime_checkable
class IStartupManager(Protocol):
    """Protocol for configuring Windows autostart on user login."""

    def is_enabled(self) -> bool:
        """Check if autostart is enabled."""
        ...

    def enable(self) -> None:
        """Enable autostart on system login."""
        ...

    def disable(self) -> None:
        """Disable autostart on system login."""
        ...
