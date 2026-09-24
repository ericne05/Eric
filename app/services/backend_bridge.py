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
        # Sprint 18.2: Do NOT unconditionally construct duplicate router via build_default_router()
        self._llm_router = llm_router
        if self._llm_router is None and self._bootstrap:
            kernel = getattr(self._bootstrap, "kernel", None)
            if not kernel and hasattr(self._bootstrap, "runtime_host"):
                kernel = getattr(self._bootstrap.runtime_host, "kernel", None)
            if kernel and getattr(kernel, "container", None):
                try:
                    if kernel.container.has(LLMRouter):
                        self._llm_router = kernel.container.resolve(LLMRouter)
                except Exception:
                    pass

        self._intent_classifier = IntentClassifier()
        self._goal_parser = GoalParser()
        self._status_listeners: List[Callable[[str], None]] = []
        self._conversation = Conversation()
        self._user_preferences: Dict[str, Any] = {}

        self.activity_logs: List[str] = []
        self.notifications: List[Dict[str, Any]] = []

    def _get_llm_router(self) -> LLMRouter:
        """Resolve authoritative LLMRouter from DI container; fallback only if container is absent."""
        if self._llm_router is not None:
            return self._llm_router

        kernel = getattr(self._bootstrap, "kernel", None)
        if not kernel and hasattr(self._bootstrap, "runtime_host"):
            kernel = getattr(self._bootstrap.runtime_host, "kernel", None)

        if kernel and getattr(kernel, "container", None):
            try:
                self._llm_router = kernel.container.resolve(LLMRouter)
                return self._llm_router
            except Exception as e:
                logger.debug(f"[BackendBridge] Could not resolve LLMRouter from DI: {e}")

        # Fallback only for detached unit tests without Kernel
        self._llm_router = build_default_router()
        return self._llm_router

    def get_session_manager(self) -> SessionManager:
        return self._session_manager

    def get_active_session(self) -> Any:
        return self._session_manager.get_active_session()

    def list_sessions(self) -> List[Any]:
        return self._session_manager.list_sessions()

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

        if intent_cls.intent != IntentType.AGENT:
            # Chat mode — LLM trả lời trực tiếp tự nhiên, không qua GoalSpec
            messages = PromptBuilder.build_chat_request(prompt, history)
            llm_response = await self._get_llm_router().chat(messages, required_capability="chat")
            reply = llm_response.content or "Xin lỗi, tôi chưa thể trả lời yêu cầu này lúc này."
            msg = self._session_manager.add_message(reply, sender="eric", status="completed")
            self._conversation.add_assistant_message(reply)
            self._notify_status("Hoàn thành")
            return msg

        # ── Bước 5: Agent mode — LLM sinh GoalSpecification JSON ──
        messages = PromptBuilder.build_agent_request(prompt, history)
        self._notify_status("Đang lập kế hoạch hành động...")
        llm_response = await self._get_llm_router().chat(messages, required_capability="goal")

        raw_output = llm_response.content or ""

        # ── Bước 6: Parse JSON -> ParsedGoalSpec ──
        spec = self._goal_parser.parse(raw_output, original_input=prompt)

        # Nếu parse thất bại, thử Repair Prompt một lần
        if spec is None:
            self._notify_status("Đang sửa lỗi cấu trúc...")
            repair_messages = PromptBuilder.build_repair_request(raw_output, "JSON không hợp lệ hoặc thiếu 'intent'")
            repair_response = await self._get_llm_router().chat(repair_messages, required_capability="goal")
            spec = self._goal_parser.parse(repair_response.content or "", original_input=prompt)

        # Nếu vẫn thất bại hoặc LLM trả plain text
        if spec is None or not spec.is_valid():
            # Chuyển sang trả lời Chat tự nhiên bằng LLM thay vì báo lỗi mẫu
            messages = PromptBuilder.build_chat_request(prompt, history)
            llm_chat = await self._get_llm_router().chat(messages, required_capability="chat")
            reply = llm_chat.content or f"Tôi đã nhận được yêu cầu '{prompt}'."
            msg = self._session_manager.add_message(reply, sender="eric", status="completed")
            self._conversation.add_assistant_message(reply)
            self._notify_status("Hoàn thành")
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
        """Chuyển ParsedGoalSpec sang GoalManager và CognitiveCoordinator để thực thi qua Core Runtime."""
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
            llm_response = await self._get_llm_router().chat(messages, required_capability="chat")
            if llm_response.content and not llm_response.content.strip().startswith("{"):
                return llm_response.content
        except Exception as e:
            logger.warning(f"[BackendBridge] Response synthesis failed: {e}")
        # Fallback
        if result.success:
            return f"✓ Đã thực hiện '{user_input}' thành công!"
        return f"❌ Không thể thực hiện '{user_input}': {result.error}"

    async def _handle_chat_fastpath(self, prompt: str, intent: IntentType) -> str:
        """Xử lý nhanh các câu chào xã giao và ghi nhớ phản hồi của Sếp."""
        lower = prompt.lower().strip()
        from datetime import datetime

        # 1. Ghi nhớ sở thích / phản hồi của Sếp
        if any(w in lower for w in ("không hỏi ngày", "không cần ngày", "chỉ hỏi giờ", "chỉ cần giờ")):
            self._user_preferences["time_only"] = True
            return "Em xin lỗi Sếp ạ! Em đã ghi nhớ: Từ bây giờ khi Sếp hỏi giờ, em sẽ chỉ trả lời giờ và không kèm theo ngày nữa ạ."

        # 2. Xử lý yêu cầu "trả lời lại" / "thử lại"
        if lower in ("trả lời lại", "nói lại", "sửa lại", "thử lại", "trả lời lại đi"):
            history = self._conversation.get_history(include_system=False)
            prev_user_msgs = [m.content for m in history if m.role == ChatRole.USER and m.content != prompt]
            if prev_user_msgs:
                last_query = prev_user_msgs[-1]
                return await self._handle_chat_fastpath(last_query, intent)
            return "Dạ Sếp! Em sẵn sàng trả lời lại ạ. Sếp muốn em trả lời lại câu hỏi nào ạ?"

        # 3. Phản ứng khi Sếp góp ý / mắng
        scolding_words = {"ngu", "dở", "dốt", "kém", "tệ", "gà", "bậy"}
        if any(w in lower for w in scolding_words):
            return "Em xin lỗi Sếp ạ! Em sẽ rút kinh nghiệm và tiếp tục hoàn thiện để hỗ trợ Sếp tốt hơn ạ."

        # 4. Hỏi giờ / ngày
        if any(w in lower for w in ("mấy giờ", "thời gian")):
            now_time = datetime.now().strftime("%H:%M:%S")
            if self._user_preferences.get("time_only", True):
                return f"Bây giờ là {now_time} ạ Sếp!"
            now_full = datetime.now().strftime("%H:%M:%S, ngày %d/%m/%Y")
            return f"Bây giờ là {now_full} ạ Sếp!"

        if any(w in lower for w in ("ngày mấy", "ngày bao nhiêu", "hôm nay ngày")):
            now_date = datetime.now().strftime("ngày %d/%m/%Y")
            return f"Hôm nay là {now_date} ạ Sếp!"

        # 5. Chào hỏi xã giao
        if any(g in lower for g in ("chào", "alo", "hello", "hi", "xin chào", "hey")):
            return "Xin chào Sếp! Em là Eric, trợ lý AI của Sếp trên Windows. Em có thể giúp gì cho Sếp hôm nay ạ?"
        if any(g in lower for g in ("cảm ơn", "thank", "tks")):
            return "Không có gì ạ! Em luôn sẵn sàng hỗ trợ Sếp."
        if any(g in lower for g in ("tạm biệt", "bye", "goodbye")):
            return "Tạm biệt Sếp! Hẹn gặp lại Sếp nhé."

        return "Dạ Sếp! Em có thể giúp gì thêm cho Sếp không ạ?"

    def get_runtime_health(self) -> Dict[str, str]:
        if not self._bootstrap.telemetry:
            return {"desktop": "ready", "vision": "ready", "browser": "ready", "knowledge": "ready"}
        snap = self._bootstrap.telemetry.snapshot()
        return snap.runtime_health or {"desktop": "ready", "vision": "ready", "browser": "ready"}
