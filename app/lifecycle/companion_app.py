"""
Windows Desktop Companion Application Coordinator (app/lifecycle/companion_app.py).

Coordinates high-level application lifecycle:
- Single-instance ownership (Named Mutex)
- System tray integration (pystray)
- Presentation visibility (hide / show separation)
- Authoritative runtime communication via EricClient
- Graceful shutdown & resource cleanup (Tray -> Client -> Runtime -> Kernel -> Lock)
"""

import asyncio
from dataclasses import dataclass
import logging
from typing import Optional

from app.client.eric_client import EricClient
from app.platform.interfaces import (
    IPresentationHost,
    ISingleInstanceLock,
    IStartupManager,
    ITrayManager,
)
from app.platform.presentation import MockPresentationHost
from app.platform.single_instance import WindowsSingleInstanceLock
from app.platform.startup import WindowsStartupManager
from app.platform.tray import PystrayTrayManager
from core.runtime.models import RuntimeEvent, RuntimeStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanionStartupResult:
    """Structured result returned by CompanionApplication.start()."""
    success: bool
    error: Optional[str] = None
    is_duplicate_instance: bool = False


class CompanionApplication:
    """
    Authoritative Windows Companion Lifecycle Manager.

    Guaranteed:
    1. Communicates with Eric engine EXCLUSIVELY through EricClient.
    2. Never touches internal Kernel, DI Container, GoalManager, or LLMRouter.
    3. Enforces single-instance ownership before booting backend runtime.
    4. Separates 'Close Window' (hide presentation) from 'Quit Eric' (full shutdown).
    5. Cleans up acquired resources deterministically if startup fails.
    """

    def __init__(
        self,
        client: Optional[EricClient] = None,
        lock: Optional[ISingleInstanceLock] = None,
        tray: Optional[ITrayManager] = None,
        presentation: Optional[IPresentationHost] = None,
        startup: Optional[IStartupManager] = None,
    ):
        self._client = client or EricClient()
        self._lock = lock or WindowsSingleInstanceLock()
        self._tray = tray or PystrayTrayManager()
        self._presentation = presentation or MockPresentationHost()
        self._startup = startup or WindowsStartupManager()

        self._is_running: bool = False
        self._is_quitting: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._quit_lock = asyncio.Lock()

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Check if companion application is actively running."""
        return self._is_running

    @property
    def is_visible(self) -> bool:
        """Check if presentation surface is currently visible."""
        return self._presentation.is_visible()

    @property
    def client(self) -> EricClient:
        """Access the public client boundary."""
        return self._client

    @property
    def status(self) -> RuntimeStatus:
        """Query current runtime lifecycle status."""
        return self._client.get_status()

    # ── Lifecycle Operations ───────────────────────────────────────────

    async def start(self, start_hidden: bool = False) -> CompanionStartupResult:
        """
        Start the companion application with deterministic lifecycle sequencing:
        1. Acquire single-instance lock (if failed -> abort immediately without starting runtime).
        2. Start runtime via EricClient (if failed -> release lock).
        3. Start system tray (if failed -> stop client, release lock).
        4. Configure tray callbacks and wire RuntimeStatus events to tray.
        5. Show presentation surface if not starting hidden.
        """
        if self._is_running:
            logger.warning("[CompanionApplication] start() called but companion is already running.")
            return CompanionStartupResult(success=True)

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

        logger.info("[CompanionApplication] Starting companion lifecycle...")

        # 1. Enforce single instance
        if not self._lock.acquire():
            logger.info("[CompanionApplication] Detected existing instance; exiting secondary process.")
            return CompanionStartupResult(
                success=False,
                error="Another instance of Eric is already running.",
                is_duplicate_instance=True,
            )

        # 2. Start runtime via EricClient
        try:
            await self._client.start()
        except Exception as exc:
            logger.error(f"[CompanionApplication] Failed to start Eric runtime: {exc}", exc_info=True)
            self._lock.release()
            return CompanionStartupResult(
                success=False,
                error=f"Runtime startup failed: {exc}",
                is_duplicate_instance=False,
            )

        # 3. Configure and start system tray
        self._tray.set_callbacks(
            on_open=self._on_tray_open,
            on_quit=self._on_tray_quit,
        )
        self._tray.set_status(self._client.get_status())

        try:
            self._tray.start()
        except Exception as exc:
            logger.error(f"[CompanionApplication] Failed to start system tray: {exc}", exc_info=True)
            try:
                await self._client.stop()
            finally:
                self._lock.release()
            return CompanionStartupResult(
                success=False,
                error=f"Tray startup failed: {exc}",
                is_duplicate_instance=False,
            )

        # 4. Wire runtime status events to tray
        self._client.subscribe("runtime.*", self._on_runtime_event)

        # 5. Presentation visibility
        if not start_hidden:
            self.show()

        self._is_running = True
        logger.info("[CompanionApplication] Companion application started successfully.")
        return CompanionStartupResult(success=True)

    def show(self) -> None:
        """Show presentation surface (e.g. from tray menu or initial launch)."""
        self._presentation.show()

    def hide(self) -> None:
        """
        Hide presentation surface.
        CRITICAL: Hiding the window keeps the companion, tray, and runtime running!
        """
        self._presentation.hide()

    async def quit(self) -> None:
        """
        Perform authoritative, graceful termination of the entire companion application.

        Sequence:
        1. Guard idempotency.
        2. Hide presentation surface.
        3. Stop system tray.
        4. Stop EricClient -> stops EricRuntimeHost -> shuts down Kernel.
        5. Release single-instance lock.
        6. Complete process cleanup (no os._exit).
        """
        async with self._quit_lock:
            if not self._is_running and not self._is_quitting:
                return

            self._is_quitting = True
            logger.info("[CompanionApplication] Initiating graceful application quit...")

            # 1. Hide presentation
            try:
                self.hide()
            except Exception as e:
                logger.warning(f"[CompanionApplication] Error hiding presentation during quit: {e}")

            # 2. Stop system tray
            try:
                self._tray.stop()
            except Exception as e:
                logger.warning(f"[CompanionApplication] Error stopping tray: {e}")

            # 3. Stop runtime via EricClient (cascades to EricRuntimeHost.stop() and Kernel.shutdown())
            try:
                await self._client.stop()
            except Exception as e:
                logger.error(f"[CompanionApplication] Error stopping Eric runtime: {e}", exc_info=True)

            # 4. Release single-instance lock (guaranteed even if client shutdown threw an exception)
            try:
                self._lock.release()
            except Exception as e:
                logger.warning(f"[CompanionApplication] Error releasing single-instance lock: {e}")

            self._is_running = False
            self._is_quitting = False
            logger.info("[CompanionApplication] Graceful companion shutdown complete.")

    # ── Internal Event Handlers ────────────────────────────────────────

    def _on_tray_open(self) -> None:
        """Callback triggered when user clicks 'Open Eric' in system tray menu."""
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop is self._loop:
                self.show()
                return
        except RuntimeError:
            pass

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.show)
        else:
            self.show()

    def _on_tray_quit(self) -> None:
        """Callback triggered when user clicks 'Quit Eric' in system tray menu."""
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop is self._loop:
                current_loop.create_task(self.quit())
                return
        except RuntimeError:
            pass

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.quit(), self._loop)
        else:
            asyncio.run(self.quit())

    def _on_runtime_event(self, event: RuntimeEvent) -> None:
        """Update tray status strictly from structured runtime status."""
        status = self._client.get_status()
        self._tray.set_status(status)
