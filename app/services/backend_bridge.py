"""
app/services/backend_bridge.py — Backend Bridge (Sprint 18 Refactor).

Luồng thực tế:
User Input
    -> IntentClassifier (fast path, no LLM for simple chat)
    -> LLMRouter.chat() (nếu cần LLM)
    -> GoalParser (JSON -> ParsedGoalSpec typed object)
    -> GoalManager.create_from_spec(spec)
    -> CognitiveCoordinator.run_cognition_loop(ctx)
    -> ExecutionResult object
    -> LLMRouter (response synthesis -> câu trả lời tự nhiên)
    -> User

LLM KHÔNG được phép gọi pyautogui, playwright, subprocess, filesystem.
LLM CHỈ sinh GoalSpecification JSON.
Mọi thực thi do DesktopRuntime / BrowserRuntime / VisionRuntime.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from app.bootstrap.app_bootstrap import AppBootstrap
from app.services.session_manager import ChatMessage, SessionManager
from core.chat.models import (
    ChatMessage as ConvMessage,
    ChatRole,
    ExecutionResult,
    IntentType,
    ParsedGoalSpec,
)
from core.chat.conversation import Conversation
from core.chat.intent_classifier import IntentClassifier
from core.chat.goal_parser import GoalParser
from core.cognition import SharedCognitiveContext
from core.goals import GoalSpecification, GoalType
from core.llm.router import LLMRouter, build_default_router
from core.llm.prompts import PromptBuilder

logger = logging.getLogger(__name__)


class BackendBridge:
    """
    Service Bridge — kết nối UI App với toàn bộ Backend Engine.
    Điều phối: IntentClassifier -> LLMRouter -> GoalParser -> GoalManager -> Runtime.
    """

    def __init__(
        self,
        bootstrap: AppBootstrap,
        session_manager: Optional[SessionManager] = None,
        notification_center: Optional[Any] = None,
        llm_router: Optional[LLMRouter] = None,
    ):
        self._bootstrap = bootstrap
        self._session_manager = session_manager or SessionManager()
        self._notification_center = notification_center
        self._llm_router = llm_router or build_default_router()
        self._intent_classifier = IntentClassifier()
        self._goal_parser = GoalParser()
        self._status_listeners: List[Callable[[str], None]] = []
        self._conversation = Conversation()

        self.activity_logs: List[str] = []
        self.notifications: List[Dict[str, Any]] = []

    def set_notification_center(self, nc: Any) -> None:
        self._notification_center = nc

    def subscribe_status(self, callback: Callable[[str], None]) -> None:
        self._status_listeners.append(callback)

    def _notify_status(self, status: str) -> None:
        self.activity_logs.append(f"[Status] {status}")
        for cb in self._status_listeners:
            cb(status)

    def push_notification(self, title: str, message: str, level: str = "info") -> None:
        self.notifications.append({"title": title, "message": message, "level": level})
        if self._notification_center:
            self._notification_center.notify(title, message, level=level)

    async def send_user_prompt(self, prompt: str) -> ChatMessage:
        """
        Xử lý input của người dùng qua toàn bộ pipeline:
        IntentClassifier -> LLMRouter -> GoalParser -> GoalManager -> Runtime -> Response Synthesis
        """
        self._session_manager.add_message(prompt, sender="user")
        self._conversation.add_user_message(prompt)

        # ── Bước 1: Phân loại ý định (fast path, không tốn LLM token) ──
        self._notify_status("Đang phân tích yêu cầu...")
        intent_cls = self._intent_classifier.classify(prompt)
        logger.info(f"[BackendBridge] Intent: {intent_cls.intent.value} (confidence={intent_cls.confidence:.2f})")

        # ── Bước 2: Fast-path CHAT (không cần LLM) ──
        if not intent_cls.requires_llm:
            reply = await self._handle_chat_fastpath(prompt, intent_cls.intent)
            msg = self._session_manager.add_message(reply, sender="eric", status="completed")
            self._conversation.add_assistant_message(reply)
            return msg

        # ── Bước 3: Khởi tạo Bootstrap nếu chưa sẵn sàng ──
        if not self._bootstrap.is_bootstrapped:
            self._notify_status("Đang khởi tạo hệ thống...")
            await self._bootstrap.initialize()

        # ── Bước 4: LLM sinh GoalSpecification hoặc câu trả lời chat ──
        self._notify_status("Đang suy nghĩ...")
        history = [
            {"role": m.role.value, "content": m.content}
            for m in self._conversation.get_history(include_system=False)
            if m.role != ChatRole.SYSTEM
        ]

        if intent_cls.intent in (IntentType.QUESTION, IntentType.MEMORY_UPDATE):
            # Chat mode — LLM trả lời trực tiếp, không cần GoalSpec
            messages = PromptBuilder.build_chat_request(prompt, history)
            llm_response = await self._llm_router.chat(messages, required_capability="chat")
            reply = llm_response.content or "Xin lỗi, tôi không thể trả lời lúc này."
            msg = self._session_manager.add_message(reply, sender="eric", status="completed")
            self._conversation.add_assistant_message(reply)
            self._notify_status("Hoàn thành")
            return msg

        # ── Bước 5: Agent mode — LLM sinh GoalSpecification JSON ──
        messages = PromptBuilder.build_agent_request(prompt, history)
        self._notify_status("Đang lập kế hoạch hành động...")
        llm_response = await self._llm_router.chat(messages, required_capability="goal")

        raw_output = llm_response.content or ""

        # ── Bước 6: Parse JSON -> ParsedGoalSpec ──
        spec = self._goal_parser.parse(raw_output, original_input=prompt)

        # Nếu parse thất bại, thử Repair Prompt một lần
        if spec is None:
            self._notify_status("Đang sửa lỗi cấu trúc...")
            repair_messages = PromptBuilder.build_repair_request(raw_output, "JSON không hợp lệ hoặc thiếu 'intent'")
            repair_response = await self._llm_router.chat(repair_messages, required_capability="goal")
            spec = self._goal_parser.parse(repair_response.content or "", original_input=prompt)

        # Nếu vẫn thất bại hoặc LLM trả plain text
        if spec is None or not spec.is_valid():
            # LLM có thể đã trả câu trả lời text thông thường
            if self._goal_parser.is_chat_response(raw_output):
                reply = raw_output
            else:
                reply = f"Tôi đã nhận được yêu cầu '{prompt}' nhưng chưa thể xác định hành động cụ thể. Bạn có thể mô tả rõ hơn không?"
            msg = self._session_manager.add_message(reply, sender="eric", status="completed")
            self._conversation.add_assistant_message(reply)
            return msg

        # ── Bước 7: GoalManager nhận ParsedGoalSpec -> Planner -> Runtime ──
        self._notify_status(f"Đang thực thi: {spec.intent}...")
        logger.info(f"[BackendBridge] Executing GoalSpec: intent='{spec.intent}' caps={spec.capability_requirements}")

        execution_result = await self._execute_spec(spec, prompt)

        # ── Bước 8: LLM tổng hợp kết quả thực thi thành câu trả lời tự nhiên ──
        self._notify_status("Đang tổng hợp kết quả...")
        reply = await self._synthesize_response(prompt, execution_result)

        self._notify_status("Hoàn thành" if execution_result.success else "Thất bại")
        if execution_result.success:
            self.push_notification("Thực thi thành công", f"Đã hoàn thành: {spec.intent}", level="success")
        else:
            self.push_notification("Thực thi thất bại", execution_result.error or "Lỗi không xác định", level="error")

        msg = self._session_manager.add_message(reply, sender="eric",
                                                 status="completed" if execution_result.success else "failed")
        self._conversation.add_assistant_message(reply)
        return msg

    async def _execute_spec(self, spec: ParsedGoalSpec, original_prompt: str) -> ExecutionResult:
        """Chuyển ParsedGoalSpec sang GoalManager và thực thi."""
        import time
        start = time.time()
        try:
            goal_description = f"{spec.intent}: {spec.parameters}"
            goal = await self._bootstrap.goal_manager.create_goal(goal_description)
            ctx = SharedCognitiveContext(goal=goal)
            res = await self._bootstrap.coordinator.run_cognition_loop(ctx)
            duration_ms = (time.time() - start) * 1000

            return ExecutionResult(
                success=res.success,
                runtime=",".join(spec.capability_requirements) or "desktop",
                intent=spec.intent,
                duration_ms=duration_ms,
                logs=[f"GoalManager executed: {goal_description}"],
                error=res.error if not res.success else None,
                output_data={"goal_id": str(getattr(goal, "id", ""))},
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error(f"[BackendBridge] Execution error: {e}")
            return ExecutionResult(
                success=False,
                runtime=",".join(spec.capability_requirements) or "unknown",
                intent=spec.intent,
                duration_ms=duration_ms,
                error=str(e),
            )

    async def _synthesize_response(self, user_input: str, result: ExecutionResult) -> str:
        """Dùng LLM để tổng hợp kết quả thực thi thành câu trả lời tự nhiên Tiếng Việt."""
        try:
            messages = PromptBuilder.build_response_synthesis(user_input, result.to_summary())
            llm_response = await self._llm_router.chat(messages, required_capability="chat")
            if llm_response.content:
                return llm_response.content
        except Exception as e:
            logger.warning(f"[BackendBridge] Response synthesis failed: {e}")
        # Fallback
        if result.success:
            return f"✓ Đã thực hiện '{user_input}' thành công ({result.duration_ms:.0f}ms)."
        return f"❌ Không thể thực hiện '{user_input}': {result.error}"

    async def _handle_chat_fastpath(self, prompt: str, intent: IntentType) -> str:
        """Xử lý nhanh các câu chào xã giao mà không cần gọi LLM."""
        lower = prompt.lower().strip()
        if any(g in lower for g in ("chào", "alo", "hello", "hi", "xin chào", "hey")):
            return (
                "Xin chào! Tôi là Eric, trợ lý AI cá nhân của bạn trên Windows.\n"
                "Tôi có thể giúp bạn mở ứng dụng, tìm kiếm thông tin, "
                "tự động hóa công việc trên Desktop và Browser.\n"
                "Bạn cần hỗ trợ gì?"
            )
        if any(g in lower for g in ("cảm ơn", "thank", "tks")):
            return "Không có gì! Tôi luôn sẵn sàng hỗ trợ bạn."
        if any(g in lower for g in ("tạm biệt", "bye", "goodbye")):
            return "Tạm biệt! Hẹn gặp lại bạn nhé."
        return "Được! Bạn cần tôi hỗ trợ gì thêm không?"

    def get_runtime_health(self) -> Dict[str, str]:
        if not self._bootstrap.telemetry:
            return {"desktop": "ready", "vision": "ready", "browser": "ready", "knowledge": "ready"}
        snap = self._bootstrap.telemetry.snapshot()
        return snap.runtime_health or {"desktop": "ready", "vision": "ready", "browser": "ready"}
