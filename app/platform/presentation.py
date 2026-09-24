"""
Presentation Host Implementations (app/platform/presentation.py).

Defines the presentation boundary separating UI window visibility (show/hide)
from the backend application lifecycle (running/quitting).
"""

import logging
from typing import Callable, Optional

from app.platform.interfaces import IPresentationHost

logger = logging.getLogger(__name__)


class MockPresentationHost(IPresentationHost):
    """
    Lightweight, headless presentation host implementation.

    Used by tests and headless runs to verify show/hide semantics without
    launching an actual desktop window framework.
    """

    def __init__(
        self,
        initially_visible: bool = False,
        on_show: Optional[Callable[[], None]] = None,
        on_hide: Optional[Callable[[], None]] = None,
    ):
        self._visible: bool = initially_visible
        self._on_show = on_show
        self._on_hide = on_hide

        self.show_call_count: int = 0
        self.hide_call_count: int = 0

    def show(self) -> None:
        """Display the presentation window."""
        self.show_call_count += 1
        self._visible = True
        logger.debug("[MockPresentationHost] Presentation shown.")
        if self._on_show:
            self._on_show()

    def hide(self) -> None:
        """Hide the presentation window without stopping the backend."""
        self.hide_call_count += 1
        self._visible = False
        logger.debug("[MockPresentationHost] Presentation hidden.")
        if self._on_hide:
            self._on_hide()

    def is_visible(self) -> bool:
        """Check if presentation is currently visible."""
        return self._visible

    def request_close(self) -> None:
        """
        Simulate user clicking the [X] button on the window.
        Crucial: Close window means HIDE, not quit!
        """
        logger.info("[MockPresentationHost] Close button clicked; hiding window.")
        self.hide()
