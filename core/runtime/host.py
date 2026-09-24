"""
Eric Runtime Host Implementation.

Authoritative host managing the backend lifecycle of Eric:
- Kernel lifecycle (boot / shutdown)
- Shared EventBus
- Capability negotiation & runtime registration
- Runtime readiness & health monitoring
- Graceful shutdown & resource cleanup
- Structured, safe runtime and goal events
- Goal execution commands & active goal tracking

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
    GoalHandle,
    GoalProgressRecord,
    GoalSnapshot,
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
            6. Subscribe to EventBus goal events to bridge to client listeners.
            7. Start runtimes (Desktop, Vision).
            8. Register runtimes with CapabilityNegotiator.
            9. Transition status -> READY.
            10. Emit 'runtime.ready'.
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

                # 4. Bridge goal events from Kernel EventBus to direct listeners
                if self._event_bus and hasattr(self._event_bus, "subscribe"):
                    self._event_bus.subscribe("goal.*", self._on_bus_goal_event)

                # 5. Start runtimes asynchronously
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

                # 6. Register runtimes with CapabilityNegotiator
                if self._negotiator and hasattr(self._negotiator, "register_runtime"):
                    if self._desktop_runtime:
                        self._negotiator.register_runtime("desktop", self._desktop_runtime)
                    if self._vision_runtime:
                        self._negotiator.register_runtime("vision", self._vision_runtime)

                # 7. Finalize transition to READY
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
            5. Transition status to STOPPED.
            6. Emit 'runtime.stopped' (prior to EventBus teardown).
            7. Shutdown Kernel (cleans plugins, container, and EventBus).
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

    # ── Goal Command Implementations ────────────────────────────────────

    async def submit_goal(self, description: str, **kwargs) -> GoalHandle:
        """
        Create a new goal in the GoalManager and return a client-safe handle.
        """
        if not self._goal_manager:
            raise RuntimeError("GoalManager is not initialized or available in DI container")

        goal = await self._goal_manager.create_goal(description, **kwargs)
        state_str = goal.state.value if hasattr(goal.state, "value") else str(goal.state)
        return GoalHandle(goal_id=goal.id, status=state_str)

    async def start_goal(self, goal_id: str) -> Dict[str, Any]:
        """
        Execute an existing goal, transitioning status to BUSY during execution
        and restoring READY upon completion/failure.
        """
        if not self._goal_manager:
            raise RuntimeError("GoalManager is not initialized or available in DI container")

        self._active_goal_id = goal_id
        self._status = RuntimeStatus.BUSY

        try:
            res = await self._goal_manager.start_goal(goal_id)
            is_success = getattr(res, "success", False)
            summary = getattr(res, "summary", "") or ""
            error = getattr(res, "error", None)

            return {
                "success": is_success,
                "goal_id": goal_id,
                "summary": summary,
                "error": error,
            }
        except Exception as exc:
            logger.error(f"[EricRuntimeHost] Goal execution error for '{goal_id}': {exc}", exc_info=True)
            return {
                "success": False,
                "goal_id": goal_id,
                "summary": "",
                "error": str(exc),
            }
        finally:
            self._active_goal_id = None
            if self._status not in (RuntimeStatus.STOPPED, RuntimeStatus.STOPPING):
                self._status = RuntimeStatus.READY

    async def execute_goal(self, description: str, **kwargs) -> Dict[str, Any]:
        """Convenience method to submit and immediately execute a goal."""
        handle = await self.submit_goal(description, **kwargs)
        return await self.start_goal(handle.goal_id)

    async def pause_goal(self, goal_id: str) -> bool:
        """Pause a running goal."""
        if not self._goal_manager or not hasattr(self._goal_manager, "pause_goal"):
            return False

        ok = await self._goal_manager.pause_goal(goal_id)
        if ok and self._active_goal_id == goal_id:
            self._status = RuntimeStatus.READY
        return bool(ok)

    async def resume_goal(self, goal_id: str) -> bool:
        """Resume a paused goal."""
        if not self._goal_manager or not hasattr(self._goal_manager, "resume_goal"):
            return False

        self._active_goal_id = goal_id
        self._status = RuntimeStatus.BUSY
        try:
            res = await self._goal_manager.resume_goal(goal_id)
            return bool(getattr(res, "success", False))
        finally:
            self._active_goal_id = None
            if self._status not in (RuntimeStatus.STOPPED, RuntimeStatus.STOPPING):
                self._status = RuntimeStatus.READY

    async def cancel_goal(self, goal_id: str) -> bool:
        """Cancel a goal."""
        if not self._goal_manager or not hasattr(self._goal_manager, "cancel_goal"):
            return False

        ok = await self._goal_manager.cancel_goal(goal_id)
        if ok and self._active_goal_id == goal_id:
            self._active_goal_id = None
            self._status = RuntimeStatus.READY
        return bool(ok)

    def get_goal_snapshot(self, goal_id: str) -> Optional[GoalSnapshot]:
        """Return a client-safe snapshot of a goal's current progress."""
        if not self._goal_manager or not hasattr(self._goal_manager, "get_goal"):
            return None

        goal = self._goal_manager.get_goal(goal_id)
        if not goal:
            return None

        progress_pct = 0.0
        completed_steps = 0
        total_steps = 0
        current_step = None

        if hasattr(goal, "progress") and goal.progress:
            progress_pct = getattr(goal.progress, "percentage", 0.0)
            completed_steps = getattr(goal.progress, "current_step_index", 0)
            total_steps = getattr(goal.progress, "total_steps", 0)

        if hasattr(goal, "plan") and goal.plan and hasattr(goal.plan, "steps"):
            total_steps = len(goal.plan.steps)
            for step in goal.plan.steps:
                if getattr(step, "status", "") == "running":
                    current_step = getattr(step, "action_name", "")
                    break

        state_val = goal.state.value if hasattr(goal.state, "value") else str(goal.state)
        error_val = goal.result.error if (hasattr(goal, "result") and goal.result) else None

        return GoalSnapshot(
            goal_id=goal.id,
            description=goal.spec.description if hasattr(goal, "spec") else "",
            status=state_val,
            progress=progress_pct,
            current_step=current_step,
            total_steps=total_steps,
            completed_steps=completed_steps,
            error=error_val,
        )

    # ── Internal Event Dispatcher ──────────────────────────────────────

    def _on_bus_goal_event(self, bus_event: Any) -> None:
        """
        Handler bridging EventBus events to direct IEricRuntime subscribers.

        Publishes with publish_to_bus=False to prevent infinite loopback.
        """
        payload = dict(bus_event.payload) if hasattr(bus_event, "payload") and isinstance(bus_event.payload, dict) else {}
        event_name = getattr(bus_event, "name", "goal.event")

        # Forward direct to runtime subscribers
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit_runtime_event(event_name, payload, publish_to_bus=False))
            if event_name == "goal.progress.updated":
                loop.create_task(self._emit_runtime_event("goal.progress", payload, publish_to_bus=False))
        except RuntimeError:
            pass

    async def _emit_runtime_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        publish_to_bus: bool = True,
    ) -> RuntimeEvent:
        """
        Construct and dispatch a structured RuntimeEvent.

        Notifies:
            1. Direct client listeners subscribed via `subscribe()`.
            2. The Kernel EventBus (if alive, available, and publish_to_bus=True).
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

        # Publish to Kernel EventBus if requested
        if publish_to_bus and self._event_bus and hasattr(self._event_bus, "publish"):
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
