"""
Backend Bridge Service.
Bridges UI ViewModels to CognitiveCoordinator, GoalManager, Telemetry, and SessionManager.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from app.bootstrap.app_bootstrap import AppBootstrap
from app.services.session_manager import ChatMessage, SessionManager
from core.cognition import SharedCognitiveContext
from core.goals import Goal, GoalSpecification, GoalState, GoalType


class BackendBridge:
    """
    Service bridging UI App to Backend Engine.
    Emits real-time UX Status Updates: Thinking -> Searching Knowledge -> Planning -> Executing -> Completed.
    """

    def __init__(
        self,
        bootstrap: AppBootstrap,
        session_manager: Optional[SessionManager] = None,
        notification_center: Optional[Any] = None,
    ):
        self._bootstrap = bootstrap
        self._session_manager = session_manager or SessionManager()
        self._notification_center = notification_center
        self._status_listeners: List[Callable[[str], None]] = []

        self.activity_logs: List[str] = []
        self.notifications: List[Dict[str, Any]] = []

    def set_notification_center(self, notification_center: Any) -> None:
        self._notification_center = notification_center

    def subscribe_status(self, callback: Callable[[str], None]) -> None:
        self._status_listeners.append(callback)

    def _notify_status(self, status: str) -> None:
        self.log_activity(f"Status update: {status}")
        for cb in self._status_listeners:
            cb(status)

    def log_activity(self, log_line: str) -> None:
        self.activity_logs.append(log_line)

    def push_notification(self, title: str, message: str, level: str = "info") -> None:
        item = {"title": title, "message": message, "level": level}
        self.notifications.append(item)
        if self._notification_center:
            self._notification_center.notify(title, message, level=level)

    async def send_user_prompt(self, prompt: str) -> ChatMessage:
        """Processes user prompt through full Backend Engine and updates UX status."""
        self._session_manager.add_message(prompt, sender="user")

        self._notify_status("Thinking...")

        if not self._bootstrap.is_bootstrapped:
            await self._bootstrap.initialize()

        self._notify_status("Searching Knowledge...")
        await asyncio.sleep(0.01)

        self._notify_status("Planning...")
        spec = GoalSpecification(description=prompt, goal_type=GoalType.MIXED)
        goal = await self._bootstrap.goal_manager.create_goal(prompt)
        ctx = SharedCognitiveContext(goal=goal)

        self._notify_status("Executing...")
        res = await self._bootstrap.coordinator.run_cognition_loop(ctx)

        if res.success:
            self._notify_status("Completed")
            self.push_notification("Goal Completed", f"Successfully finished: {prompt}", level="success")
            reply_text = f"✓ Completed goal: '{prompt}'. Executed across registered runtimes."
            return self._session_manager.add_message(reply_text, sender="eric", status="completed")
        else:
            self._notify_status("Failed")
            self.push_notification("Goal Failed", res.error or "Execution error", level="error")
            reply_text = f"❌ Execution failed: {res.error}"
            return self._session_manager.add_message(reply_text, sender="eric", status="failed")

    def get_runtime_health(self) -> Dict[str, str]:
        if not self._bootstrap.telemetry:
            return {"desktop": "ready", "vision": "ready", "browser": "ready", "knowledge": "ready"}
        snap = self._bootstrap.telemetry.snapshot()
        return snap.runtime_health or {"desktop": "ready", "vision": "ready", "browser": "ready", "knowledge": "ready"}
