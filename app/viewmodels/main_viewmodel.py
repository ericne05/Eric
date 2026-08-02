"""
Main App ViewModel.
Binds state for UI Components: Chat, Timeline, Runtime Status, Goal Dashboard, Activity Console, and Notifications.
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.services.backend_bridge import BackendBridge
from app.services.session_manager import ChatMessage, ChatSession


class MainViewModel:
    """
    Main App ViewModel managing desktop client state.
    """

    def __init__(self, bridge: BackendBridge):
        self.bridge = bridge
        self.current_status: str = "Ready"
        self.goal_progress: float = 0.0
        self.timeline_steps: List[Dict[str, Any]] = []
        self.is_processing: bool = False

        self.bridge.subscribe_status(self._on_status_changed)

    def _on_status_changed(self, new_status: str) -> None:
        self.current_status = new_status

        # Update progress based on status
        if new_status == "Thinking...":
            self.goal_progress = 10.0
            self.is_processing = True
        elif new_status == "Searching Knowledge...":
            self.goal_progress = 25.0
        elif new_status == "Planning...":
            self.goal_progress = 50.0
        elif new_status == "Executing...":
            self.goal_progress = 75.0
        elif new_status == "Completed":
            self.goal_progress = 100.0
            self.is_processing = False
        elif new_status == "Failed":
            self.is_processing = False

    async def submit_prompt(self, prompt: str) -> ChatMessage:
        self.timeline_steps = [
            {"step": "Observe Environment", "status": "completed"},
            {"step": "Query Knowledge Graph", "status": "completed"},
            {"step": "Plan Execution Steps", "status": "completed"},
            {"step": "Execute Step Actions", "status": "running"},
        ]
        res = await self.bridge.send_user_prompt(prompt)
        self.timeline_steps[3]["status"] = "completed"
        return res

    def get_messages(self) -> List[ChatMessage]:
        session = self.bridge._session_manager.get_active_session()
        return session.messages

    def get_sessions(self) -> List[ChatSession]:
        return self.bridge._session_manager.list_sessions()

    def get_activity_logs(self) -> List[str]:
        return self.bridge.activity_logs

    def get_notifications(self) -> List[Dict[str, Any]]:
        return self.bridge.notifications

    def get_runtime_health(self) -> Dict[str, str]:
        return self.bridge.get_runtime_health()
