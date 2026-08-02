"""
Backend Bridge Service.
Bridges UI ViewModels to CognitiveCoordinator, GoalManager, Telemetry, and SessionManager.
Hỗ trợ Tiếng Việt tự nhiên cho người dùng.
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
        self.log_activity(f"Cập nhật trạng thái: {status}")
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
        """Processes user prompt through full Backend Engine and updates UX status in natural Vietnamese."""
        self._session_manager.add_message(prompt, sender="user")

        prompt_clean = prompt.strip().lower()

        # Xử lý các câu chào / giao tiếp Tiếng Việt
        greetings = ("alo", "chao", "chào", "hello", "hi", "noi tieng viet di", "nói tiếng việt đi", "tieng viet")
        if any(g in prompt_clean for g in greetings) and len(prompt_clean) < 25:
            self._notify_status("Phản hồi...")
            reply_text = (
                "Chào bạn! Eric nghe đây. Tôi là Trợ lý AI cá nhân của bạn trên Windows.\n"
                "Tôi đã sẵn sàng tự động hóa công việc Browser, Desktop và Vision giúp bạn!"
            )
            return self._session_manager.add_message(reply_text, sender="eric", status="completed")

        self._notify_status("Đang suy nghĩ...")

        if not self._bootstrap.is_bootstrapped:
            await self._bootstrap.initialize()

        self._notify_status("Đang truy vấn tri thức...")
        await asyncio.sleep(0.01)

        self._notify_status("Đang lập kế hoạch...")
        spec = GoalSpecification(description=prompt, goal_type=GoalType.MIXED)
        goal = await self._bootstrap.goal_manager.create_goal(prompt)
        ctx = SharedCognitiveContext(goal=goal)

        self._notify_status("Đang thực thi...")
        res = await self._bootstrap.coordinator.run_cognition_loop(ctx)

        if res.success:
            self._notify_status("Hoàn thành")
            self.push_notification("Mục tiêu hoàn thành", f"Đã thực thi thành công: {prompt}", level="success")
            reply_text = f"✓ Đã hoàn thành mục tiêu: '{prompt}'. Đã thực thi qua các runtime."
            return self._session_manager.add_message(reply_text, sender="eric", status="completed")
        else:
            self._notify_status("Thất bại")
            self.push_notification("Mục tiêu thất bại", res.error or "Lỗi thực thi", level="error")
            reply_text = f"❌ Thực thi thất bại: {res.error}"
            return self._session_manager.add_message(reply_text, sender="eric", status="failed")

    def get_runtime_health(self) -> Dict[str, str]:
        if not self._bootstrap.telemetry:
            return {"desktop": "ready", "vision": "ready", "browser": "ready", "knowledge": "ready"}
        snap = self._bootstrap.telemetry.snapshot()
        return snap.runtime_health or {"desktop": "ready", "vision": "ready", "browser": "ready", "knowledge": "ready"}
