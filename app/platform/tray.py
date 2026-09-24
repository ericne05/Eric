"""
Desktop System Tray Implementations (app/platform/tray.py).

Provides:
- PystrayTrayManager: Production Windows system tray using pystray and Pillow.
- MockTrayManager: Headless mock for fast, reliable unit/CI testing without GUI threads.
"""

import logging
from typing import Callable, Optional

from app.platform.interfaces import ITrayManager
from core.runtime.models import RuntimeStatus

logger = logging.getLogger(__name__)


class PystrayTrayManager(ITrayManager):
    """
    Windows System Tray implementation using pystray.
    Runs non-blockingly via run_detached().
    """

    def __init__(
        self,
        on_open: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self._on_open = on_open
        self._on_quit = on_quit
        self._status: RuntimeStatus = RuntimeStatus.CREATED
        self._icon = None
        self._is_running: bool = False

    def set_callbacks(
        self,
        on_open: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_open is not None:
            self._on_open = on_open
        if on_quit is not None:
            self._on_quit = on_quit

    def _create_icon_image(self):
        """Generate a clean 64x64 RGBA icon image using Pillow."""
        try:
            from PIL import Image, ImageDraw

            # 64x64 RGBA image with deep blue/purple circular badge and white 'E'
            image = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # Outer circle
            draw.ellipse((4, 4, 60, 60), fill=(24, 119, 242, 255), outline=(255, 255, 255, 200), width=2)

            # Center square 'E' representation
            draw.rectangle((20, 18, 44, 24), fill=(255, 255, 255, 255))
            draw.rectangle((20, 24, 26, 46), fill=(255, 255, 255, 255))
            draw.rectangle((20, 29, 38, 35), fill=(255, 255, 255, 255))
            draw.rectangle((20, 40, 44, 46), fill=(255, 255, 255, 255))

            return image
        except Exception as e:
            logger.warning(f"[PystrayTrayManager] Error generating icon image: {e}")
            from PIL import Image
            return Image.new("RGB", (64, 64), color=(30, 144, 255))

    def _build_menu(self):
        """Construct the system tray menu matching Eric companion specifications."""
        import pystray

        status_text = f"Status: {self._status.value.upper()}"

        def _handle_open(icon, item):
            if self._on_open:
                self._on_open()

        def _handle_quit(icon, item):
            if self._on_quit:
                self._on_quit()

        return pystray.Menu(
            pystray.MenuItem("Eric AI Assistant", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Eric", _handle_open, default=True),
            pystray.MenuItem(status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Eric", _handle_quit),
        )

    def start(self) -> None:
        """Start the background system tray icon."""
        if self._is_running:
            return

        try:
            import pystray

            image = self._create_icon_image()
            menu = self._build_menu()
            self._icon = pystray.Icon(
                name="EricDesktopAssistant",
                icon=image,
                title=f"Eric ({self._status.value})",
                menu=menu,
            )
            # Run detached so it doesn't block asyncio main loop
            self._icon.run_detached()
            self._is_running = True
            logger.info("[PystrayTrayManager] System tray icon started.")
        except Exception as e:
            logger.error(f"[PystrayTrayManager] Failed to start system tray icon: {e}", exc_info=True)
            self._is_running = False
            raise

    def stop(self) -> None:
        """Stop and remove the system tray icon."""
        if not self._is_running or self._icon is None:
            return

        try:
            self._icon.stop()
            logger.info("[PystrayTrayManager] System tray icon stopped.")
        except Exception as e:
            logger.warning(f"[PystrayTrayManager] Error stopping tray icon: {e}")
        finally:
            self._is_running = False
            self._icon = None

    def set_status(self, status: RuntimeStatus) -> None:
        """Update tray status display based on authoritative RuntimeStatus."""
        self._status = status
        if self._icon and self._is_running:
            try:
                self._icon.title = f"Eric ({self._status.value})"
                self._icon.menu = self._build_menu()
                if hasattr(self._icon, "update_menu"):
                    self._icon.update_menu()
            except Exception as e:
                logger.debug(f"[PystrayTrayManager] Tray menu update omitted: {e}")

    def is_running(self) -> bool:
        return self._is_running


class MockTrayManager(ITrayManager):
    """
    Headless mock tray manager for reliable, fast test execution.
    """

    def __init__(
        self,
        on_open: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        fail_on_start: bool = False,
    ):
        self._on_open = on_open
        self._on_quit = on_quit
        self._fail_on_start = fail_on_start
        self._status: RuntimeStatus = RuntimeStatus.CREATED
        self._is_running: bool = False

        self.start_call_count: int = 0
        self.stop_call_count: int = 0
        self.status_history: list = []

    def set_callbacks(
        self,
        on_open: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_open is not None:
            self._on_open = on_open
        if on_quit is not None:
            self._on_quit = on_quit

    def start(self) -> None:
        self.start_call_count += 1
        if self._fail_on_start:
            raise RuntimeError("Simulated tray startup failure")
        self._is_running = True

    def stop(self) -> None:
        self.stop_call_count += 1
        self._is_running = False

    def set_status(self, status: RuntimeStatus) -> None:
        self._status = status
        self.status_history.append(status)

    def is_running(self) -> bool:
        return self._is_running

    def simulate_open(self) -> None:
        """Simulate user selecting 'Open Eric' from tray menu."""
        if self._on_open:
            self._on_open()

    def simulate_quit(self) -> None:
        """Simulate user selecting 'Quit Eric' from tray menu."""
        if self._on_quit:
            self._on_quit()
