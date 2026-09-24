"""
Eric Client Boundary (app/client/eric_client.py).

Provides an application-facing client abstraction for the Eric Desktop Assistant.
Interacts with the runtime exclusively through IEricRuntime, completely isolating
the UI layer from backend internals (Kernel, EventBus, GoalManager, LLMRouter).

Designed to be transport-agnostic: the Desktop UI or CLI can switch from in-process
calls to local IPC (Named Pipes, Sockets, MCP) without any UI changes.
"""

from typing import Any, Callable, Coroutine, Dict, Optional, Union

from core.runtime.client_interface import IEricRuntime, RuntimeEventListener
from core.runtime.models import (
    GoalHandle,
    GoalSnapshot,
    RuntimeEvent,
    RuntimeSnapshot,
    RuntimeStatus,
)


class EricClient:
    """
    Authoritative client-side interface for Eric Desktop applications.

    Encapsulates all runtime communication behind IEricRuntime.
    Guaranteed NOT to expose Kernel, EventBus, GoalManager, or DI Container instances.
    """

    def __init__(self, runtime: Optional[IEricRuntime] = None):
        """
        Initialize the EricClient.

        Args:
            runtime: Optional IEricRuntime implementation (e.g. EricRuntimeHost in-process,
                     or a future IPC client). If None, defaults to in-process EricRuntimeHost.
        """
        if runtime is None:
            from core.runtime.host import EricRuntimeHost
            runtime = EricRuntimeHost()
        self._runtime: IEricRuntime = runtime

    # ── Lifecycle Operations ───────────────────────────────────────────

    async def start(self) -> None:
        """Start the underlying Eric runtime."""
        await self._runtime.start()

    async def stop(self) -> None:
        """Gracefully stop the underlying Eric runtime."""
        await self._runtime.stop()

    def get_status(self) -> RuntimeStatus:
        """Get the current high-level runtime lifecycle status."""
        return self._runtime.get_status()

    def get_snapshot(self) -> RuntimeSnapshot:
        """
        Get a transport-safe, serializable snapshot of runtime state.

        Guaranteed to contain no live internal service objects.
        """
        return self._runtime.get_snapshot()

    # ── Goal Operations ────────────────────────────────────────────────

    async def submit_goal(self, description: str, **kwargs) -> GoalHandle:
        """
        Submit a new goal for execution.

        Returns a client-safe GoalHandle with the generated goal_id.
        """
        return await self._runtime.submit_goal(description, **kwargs)

    async def start_goal(self, goal_id: str) -> Dict[str, Any]:
        """
        Execute an already submitted goal.

        Transitions host status to BUSY during execution, then back to READY.
        Returns a serializable result summary.
        """
        return await self._runtime.start_goal(goal_id)

    async def execute_goal(self, description: str, **kwargs) -> Dict[str, Any]:
        """
        Create and execute a goal end-to-end.

        Convenience wrapper around submit_goal + start_goal.
        """
        return await self._runtime.execute_goal(description, **kwargs)

    async def pause_goal(self, goal_id: str) -> bool:
        """
        Pause an actively running goal.

        Returns True if paused successfully, False otherwise.
        """
        return await self._runtime.pause_goal(goal_id)

    async def resume_goal(self, goal_id: str) -> bool:
        """
        Resume a previously paused goal.

        Returns True if resumed and completed successfully, False otherwise.
        """
        return await self._runtime.resume_goal(goal_id)

    async def cancel_goal(self, goal_id: str) -> bool:
        """
        Cancel a running or queued goal.

        Returns True if cancelled, False otherwise.
        """
        return await self._runtime.cancel_goal(goal_id)

    def get_goal_snapshot(self, goal_id: str) -> Optional[GoalSnapshot]:
        """
        Get a client-safe snapshot of a goal's state.

        Returns None if the goal is not found.
        """
        return self._runtime.get_goal_snapshot(goal_id)

    # ── Event Subscription ─────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: RuntimeEventListener) -> None:
        """
        Subscribe a listener to structured runtime and goal events.

        Args:
            event_type: Event type name (e.g. 'runtime.ready', 'goal.*', 'goal.progress') or '*' for all.
            handler: Callable accepting a RuntimeEvent (sync or coroutine).
        """
        self._runtime.subscribe(event_type, handler)

    def unsubscribe(self, event_type: str, handler: RuntimeEventListener) -> None:
        """
        Unsubscribe a listener from runtime events.

        Args:
            event_type: Event type name or '*'.
            handler: The previously subscribed callable.
        """
        self._runtime.unsubscribe(event_type, handler)
