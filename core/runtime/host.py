"""
Eric Runtime Host Implementation.

Authoritative host managing the backend lifecycle of Eric:
- Kernel lifecycle (boot / shutdown)
- Shared EventBus
- Capability negotiation & runtime registration
- Runtime readiness & health monitoring
- Graceful shutdown & resource cleanup
- Structured, safe runtime events

Follows the Single Composition Root principle established in Sprint 17.5:
All services are resolved via Kernel DI; RuntimeHost coordinates, it does not rebuild.
"""

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from core.events.event import Event
from core.events.event_bus import EventBus
from core.runtime.client_interface import IEricRuntime, RuntimeEventListener
from core.runtime.models import (
    RuntimeErrorInfo,
    RuntimeEvent,
    RuntimeSnapshot,
    RuntimeStatus,
)

logger = logging.getLogger(__name__)


class EricRuntimeHost(IEricRuntime):
    """
    Authoritative backend lifecycle manager for Eric.

    Implements IEricRuntime as a transport-agnostic host. Can be driven directly
    in-process by AppBootstrap / DesktopClient, or behind local IPC adapters.
    """

    def __init__(self, kernel: Optional[Any] = None):
        """
        Initialize the Runtime Host.

        Args:
            kernel: Optional pre-configured Kernel instance (useful for unit tests with mocks).
                    If None, Kernel will be booted via bootstrap() upon start().
        """
        self._kernel = kernel
        self._event_bus: Optional[EventBus] = None
        self._status: RuntimeStatus = RuntimeStatus.CREATED
        self._started_at: Optional[datetime] = None
        self._active_goal_id: Optional[str] = None
        self._last_error: Optional[RuntimeErrorInfo] = None

        # Resolved DI services (internal only)
        self._negotiator: Optional[Any] = None
        self._desktop_runtime: Optional[Any] = None
        self._vision_runtime: Optional[Any] = None
        self._goal_manager: Optional[Any] = None
        self._coordinator: Optional[Any] = None

        # Direct event listeners (event_type -> list of handlers)
        self._listeners: Dict[str, List[RuntimeEventListener]] = {}
        self._lock = asyncio.Lock()

    # ── IEricRuntime Interface Implementation ──────────────────────────

    def get_status(self) -> RuntimeStatus:
        """Return current runtime lifecycle status."""
        return self._status

    def get_snapshot(self) -> RuntimeSnapshot:
        """
        Return a clean, serializable snapshot of runtime state.
        Guaranteed to contain no live internal service objects.
        """
        return RuntimeSnapshot(
            status=self._status,
            started_at=self._started_at,
            active_goal_id=self._active_goal_id,
            last_error=self._last_error,
        )

    def subscribe(self, event_type: str, handler: RuntimeEventListener) -> None:
        """Subscribe a listener to structured runtime events."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if handler not in self._listeners[event_type]:
            self._listeners[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: RuntimeEventListener) -> None:
        """Unsubscribe a listener from runtime events."""
        if event_type in self._listeners and handler in self._listeners[event_type]:
            self._listeners[event_type].remove(handler)

    async def start(self) -> None:
        """
        Start the Eric Runtime Host and boot all required subsystems.

        Lifecycle sequence:
            1. Check idempotency (if READY, no-op).
            2. Transition status -> STARTING.
            3. Emit 'runtime.starting'.
            4. Boot Kernel (or use provided Kernel).
            5. Resolve services from DI Container.
            6. Start runtimes (Desktop, Vision).
            7. Register runtimes with CapabilityNegotiator.
            8. Transition status -> READY.
            9. Emit 'runtime.ready'.

        On failure:
            - Transition status -> ERROR.
            - Record structured RuntimeErrorInfo (safe, no secrets).
            - Log full exception traceback.
            - Emit 'runtime.error'.
            - Re-raise exception.
        """
        async with self._lock:
            if self._status == RuntimeStatus.READY:
                logger.warning("[EricRuntimeHost] start() called but runtime is already READY (idempotent)")
                return

            if self._status == RuntimeStatus.STARTING:
                logger.warning("[EricRuntimeHost] start() called but runtime is already STARTING")
                return

            self._status = RuntimeStatus.STARTING
            self._last_error = None
            logger.info("[EricRuntimeHost] Starting runtime host...")

            # Emit initial starting event if event bus or direct listeners exist
            await self._emit_runtime_event("runtime.starting", {})

            try:
                # 1. Boot Kernel if needed
                if self._kernel is None:
                    from core.kernel.bootstrap import bootstrap
                    self._kernel = bootstrap()
                elif hasattr(self._kernel, "state") and hasattr(self._kernel, "boot"):
                    from core.kernel.lifecycle import SystemState
                    if self._kernel.state == SystemState.CREATED:
                        self._kernel.boot()

                # 2. Resolve EventBus from Kernel DI Container
                if hasattr(self._kernel, "event_bus"):
                    self._event_bus = self._kernel.event_bus
                elif hasattr(self._kernel, "container"):
                    try:
                        self._event_bus = self._kernel.container.resolve(EventBus)
                    except Exception:
                        pass

                # 3. Resolve required runtime and orchestration services from DI Container
                container = getattr(self._kernel, "container", None)
                if container:
                    from core.runtime.capability import CapabilityNegotiator
                    from core.desktop.interfaces import IDesktopRuntime
                    from core.vision.interfaces import IVisionRuntime
                    from core.goals import GoalManager
                    from core.cognition import CognitiveCoordinator

                    if hasattr(container, "resolve"):
                        try:
                            self._negotiator = container.resolve(CapabilityNegotiator)
                        except Exception:
                            pass
                        try:
                            self._desktop_runtime = container.resolve(IDesktopRuntime)
                        except Exception:
                            pass
                        try:
                            self._vision_runtime = container.resolve(IVisionRuntime)
                        except Exception:
                            pass
                        try:
                            self._goal_manager = container.resolve(GoalManager)
                        except Exception:
                            pass
                        try:
                            self._coordinator = container.resolve(CognitiveCoordinator)
                        except Exception:
                            pass

                # 4. Start runtimes asynchronously
                active_runtimes = []
                if self._desktop_runtime and hasattr(self._desktop_runtime, "start"):
                    res = self._desktop_runtime.start()
                    if inspect.isawaitable(res):
                        await res
                    active_runtimes.append("desktop")
                if self._vision_runtime and hasattr(self._vision_runtime, "start"):
                    res = self._vision_runtime.start()
                    if inspect.isawaitable(res):
                        await res
                    active_runtimes.append("vision")

                # 5. Register runtimes with CapabilityNegotiator
                if self._negotiator and hasattr(self._negotiator, "register_runtime"):
                    if self._desktop_runtime:
                        self._negotiator.register_runtime("desktop", self._desktop_runtime)
                    if self._vision_runtime:
                        self._negotiator.register_runtime("vision", self._vision_runtime)

                # 6. Finalize transition to READY
                self._status = RuntimeStatus.READY
                self._started_at = datetime.now(timezone.utc)
                logger.info("[EricRuntimeHost] Runtime Host is READY.")

                await self._emit_runtime_event(
                    "runtime.ready",
                    {
                        "status": "ready",
                        "runtimes": active_runtimes,
                    },
                )

            except Exception as exc:
                self._status = RuntimeStatus.ERROR
                self._last_error = RuntimeErrorInfo(
                    code="STARTUP_FAILED",
                    message=str(exc) or type(exc).__name__,
                    recoverable=False,
                    timestamp=datetime.now(timezone.utc),
                )
                logger.error(f"[EricRuntimeHost] Startup failed: {exc}", exc_info=True)

                await self._emit_runtime_event(
                    "runtime.error",
                    {
                        "code": self._last_error.code,
                        "message": self._last_error.message,
                        "recoverable": self._last_error.recoverable,
                    },
                )
                raise

    async def stop(self) -> None:
        """
        Gracefully stop the runtime host and underlying services.

        Lifecycle sequence:
            1. Check idempotency (if STOPPED, no-op).
            2. Transition status -> STOPPING.
            3. Emit 'runtime.stopping'.
            4. Stop runtimes (Desktop, Vision).
            5. Emit 'runtime.stopped' (prior to EventBus teardown).
            6. Shutdown Kernel (cleans plugins, container, and EventBus).
            7. Transition status -> STOPPED.
        """
        async with self._lock:
            if self._status == RuntimeStatus.STOPPED:
                logger.warning("[EricRuntimeHost] stop() called but runtime is already STOPPED (idempotent)")
                return

            self._status = RuntimeStatus.STOPPING
            logger.info("[EricRuntimeHost] Stopping runtime host...")

            # Emit stopping event
            await self._emit_runtime_event("runtime.stopping", {})

            # 1. Stop runtimes
            if self._desktop_runtime:
                try:
                    if hasattr(self._desktop_runtime, "stop"):
                        res = self._desktop_runtime.stop()
                        if inspect.isawaitable(res):
                            await res
                    elif hasattr(self._desktop_runtime, "shutdown"):
                        res = self._desktop_runtime.shutdown()
                        if inspect.isawaitable(res):
                            await res
                except Exception as e:
                    logger.warning(f"[EricRuntimeHost] Error stopping desktop runtime: {e}")

            if self._vision_runtime:
                try:
                    if hasattr(self._vision_runtime, "shutdown"):
                        res = self._vision_runtime.shutdown()
                        if inspect.isawaitable(res):
                            await res
                    elif hasattr(self._vision_runtime, "stop"):
                        res = self._vision_runtime.stop()
                        if inspect.isawaitable(res):
                            await res
                except Exception as e:
                    logger.warning(f"[EricRuntimeHost] Error stopping vision runtime: {e}")

            # 2. Transition status to STOPPED
            self._status = RuntimeStatus.STOPPED
            self._started_at = None
            self._active_goal_id = None

            # 3. Emit stopped event to direct listeners and EventBus before bus is disposed
            await self._emit_runtime_event("runtime.stopped", {})

            # 4. Shutdown Kernel (idempotent; disposes container and shuts down EventBus)
            if self._kernel and hasattr(self._kernel, "shutdown"):
                try:
                    self._kernel.shutdown()
                except Exception as e:
                    logger.error(f"[EricRuntimeHost] Error shutting down Kernel: {e}", exc_info=True)

            logger.info("[EricRuntimeHost] Runtime Host is STOPPED.")

    # ── Internal Event Dispatcher ──────────────────────────────────────

    async def _emit_runtime_event(self, event_type: str, payload: Dict[str, Any]) -> RuntimeEvent:
        """
        Construct and dispatch a structured RuntimeEvent.

        Notifies:
            1. Direct client listeners subscribed via `subscribe()`.
            2. The Kernel EventBus (if alive and available).
        """
        event = RuntimeEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
        )

        # Notify direct listeners (for event_type and wildcard '*')
        target_listeners = list(self._listeners.get(event_type, [])) + list(self._listeners.get("*", []))
        for listener in target_listeners:
            try:
                result = listener(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as listener_exc:
                logger.warning(f"[EricRuntimeHost] Event listener failed for '{event_type}': {listener_exc}")

        # Publish to Kernel EventBus if available
        if self._event_bus and hasattr(self._event_bus, "publish"):
            try:
                bus_event = Event.create(
                    name=event_type,
                    source="runtime.host",
                    payload=payload,
                )
                await self._event_bus.publish(bus_event)
            except Exception as bus_exc:
                logger.debug(f"[EricRuntimeHost] EventBus publish for '{event_type}' omitted: {bus_exc}")

        return event

    # ── Internal Accessors (for AppBootstrap backward-compatibility) ───

    @property
    def kernel(self) -> Optional[Any]:
        return self._kernel

    @property
    def event_bus(self) -> Optional[EventBus]:
        return self._event_bus

    @property
    def negotiator(self) -> Optional[Any]:
        return self._negotiator

    @property
    def desktop_runtime(self) -> Optional[Any]:
        return self._desktop_runtime

    @property
    def vision_runtime(self) -> Optional[Any]:
        return self._vision_runtime

    @property
    def goal_manager(self) -> Optional[Any]:
        return self._goal_manager

    @property
    def coordinator(self) -> Optional[Any]:
        return self._coordinator
