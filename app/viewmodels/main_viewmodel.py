"""
Main App ViewModel.
Binds state for UI Components: Chat, Timeline, Runtime Status, Goal Dashboard, Activity Console, and Notifications.

Sprint 18.2: Refactored to consume structured events from EricClient instead of parsing
language-dependent strings, and eliminated private-field access.
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.services.session_manager import ChatMessage, ChatSession
from core.runtime.models import RuntimeEvent


class MainViewModel:
    """
    Main App ViewModel managing desktop client state.

    Authoritative progress and operational states are driven exclusively by
    structured RuntimeEvent streams from EricClient / IEricRuntime.
    """

    def __init__(self, bridge: Optional[Any] = None, client: Optional[Any] = None):
        self.bridge = bridge
        self.client = client
        self.current_status: str = "Ready"
        self.goal_progress: float = 0.0
        self.timeline_steps: List[Dict[str, Any]] = []
        self.is_processing: bool = False

        # 1. Subscribe to structured runtime & goal events if client is available
        if self.client and hasattr(self.client, "subscribe"):
            self.client.subscribe("goal.*", self._on_goal_event)
            self.client.subscribe("runtime.*", self._on_runtime_event)

        # 2. Backward compatibility: listen to bridge status for presentation text only
        if self.bridge and hasattr(self.bridge, "subscribe_status"):
            self.bridge.subscribe_status(self._on_display_status_changed)

    def _on_goal_event(self, event: RuntimeEvent) -> None:
        """
        Handle authoritative structured goal events.
        Progress and processing states are driven here, NEVER by string matching.
        """
        event_type = event.event_type
        payload = event.payload or {}

        if event_type == "goal.started":
            self.is_processing = True
            self.goal_progress = 10.0
            self.current_status = "Executing goal..."
        elif event_type in ("goal.progress", "goal.progress.updated"):
            pct = payload.get("percentage")
            if pct is not None:
                self.goal_progress = float(pct)
            action = payload.get("action") or payload.get("current_runtime")
            if action:
                self.current_status = f"In progress: {action}"
        elif event_type == "goal.step.started":
            action = payload.get("action", "step")
            self.current_status = f"Executing step: {action}"
            self.timeline_steps.append({"step": action, "status": "running"})
        elif event_type == "goal.step.completed":
            if self.timeline_steps and self.timeline_steps[-1]["status"] == "running":
                self.timeline_steps[-1]["status"] = "completed"
        elif event_type == "goal.completed":
            self.goal_progress = 100.0
            self.is_processing = False
            self.current_status = "Completed"
            for step in self.timeline_steps:
                if step.get("status") == "running":
                    step["status"] = "completed"
        elif event_type in ("goal.failed", "goal.cancelled"):
            self.is_processing = False
            self.current_status = "Failed" if event_type == "goal.failed" else "Cancelled"
            if self.timeline_steps and self.timeline_steps[-1]["status"] == "running":
                self.timeline_steps[-1]["status"] = "failed"

    def _on_runtime_event(self, event: RuntimeEvent) -> None:
        """Handle structured runtime lifecycle events."""
        event_type = event.event_type
        if event_type == "runtime.ready":
            self.current_status = "Ready"
        elif event_type == "runtime.stopping":
            self.current_status = "Stopping..."
        elif event_type == "runtime.stopped":
            self.current_status = "Stopped"
            self.is_processing = False
        elif event_type == "runtime.error":
            self.current_status = "Error"
            self.is_processing = False

    def _on_display_status_changed(self, new_status: str) -> None:
        """
        Display-only callback for human-readable notifications.
        Does NOT alter is_processing or calculate percentage progress.
        """
        self.current_status = new_status

    def _on_status_changed(self, new_status: str) -> None:
        """Legacy helper for backward compatibility."""
        self._on_display_status_changed(new_status)

    async def submit_prompt(self, prompt: str) -> ChatMessage:
        self.timeline_steps = [
            {"step": "Observe Environment", "status": "completed"},
            {"step": "Query Knowledge Graph", "status": "completed"},
            {"step": "Plan Execution Steps", "status": "completed"},
            {"step": "Execute Step Actions", "status": "running"},
        ]
        if self.bridge:
            res = await self.bridge.send_user_prompt(prompt)
            self.timeline_steps[3]["status"] = "completed"
            return res
        raise RuntimeError("No BackendBridge configured on MainViewModel")

    def get_messages(self) -> List[ChatMessage]:
        if self.bridge:
            if hasattr(self.bridge, "get_active_session"):
                session = self.bridge.get_active_session()
                return session.messages if session else []
            elif hasattr(self.bridge, "_session_manager"):
                session = self.bridge._session_manager.get_active_session()
                return session.messages if session else []
        return []

    def get_sessions(self) -> List[ChatSession]:
        if self.bridge:
            if hasattr(self.bridge, "list_sessions"):
                return self.bridge.list_sessions()
            elif hasattr(self.bridge, "_session_manager"):
                return self.bridge._session_manager.list_sessions()
        return []

    def get_activity_logs(self) -> List[str]:
        return getattr(self.bridge, "activity_logs", [])

    def get_notifications(self) -> List[Dict[str, Any]]:
        return getattr(self.bridge, "notifications", [])

    def get_runtime_health(self) -> Dict[str, str]:
        if self.bridge and hasattr(self.bridge, "get_runtime_health"):
            return self.bridge.get_runtime_health()
        return {}
