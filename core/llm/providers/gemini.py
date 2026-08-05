"""
core/llm/providers/gemini.py — Google Gemini LLM Provider.

Kết nối thực tế với Gemini API (google-generativeai SDK hoặc REST fallback).
LLM KHÔNG được phép điều khiển hệ thống — chỉ được sinh GoalSpecification JSON.
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.llm.interfaces import ILLMProvider
from core.llm.models import LLMMessage, LLMResponse, ModelConfig
from core.llm.enums import FinishReason, MessageRole

logger = logging.getLogger(__name__)


class GeminiProvider(ILLMProvider):
    """
    Google Gemini LLM Provider.
    Hỗ trợ: google-generativeai SDK (ưu tiên) hoặc REST API fallback.
    """

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._model_name = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._sdk_available = False
        self._genai = None
        self._client = None
        self._use_new_genai = False

        self._try_init_sdk()

    def _try_init_sdk(self) -> None:
        """Thử khởi tạo Google GenAI SDK (google.genai hoặc google.generativeai)."""
        if not self._api_key:
            self._sdk_available = False
            return

        try:
            from google import genai  # type: ignore
            self._client = genai.Client(api_key=self._api_key)
            self._use_new_genai = True
            self._sdk_available = True
            logger.info("[GeminiProvider] Using modern google.genai SDK Client")
            return
        except Exception as e:
            logger.debug(f"[GeminiProvider] google.genai init: {e}")

        try:
            import google.generativeai as genai_old  # type: ignore
            genai_old.configure(api_key=self._api_key)
            self._genai = genai_old
            self._use_new_genai = False
            self._sdk_available = True
            logger.info("[GeminiProvider] Using google.generativeai SDK")
        except Exception as e:
            logger.debug(f"[GeminiProvider] google.generativeai init: {e}")
            self._sdk_available = False

    async def generate(
        self,
        messages: List[LLMMessage],
        tools=None,
        model: Optional[ModelConfig] = None,
        cancellation_token=None,
        stream: bool = False,
    ) -> LLMResponse:
        model_name = model.name if model else self._model_name
        start = time.time()

        # Dynamic re-check API key từ môi trường nếu trước đó chưa có
        if not self._api_key:
            env_key = os.environ.get("GEMINI_API_KEY", "")
            if env_key:
                self._api_key = env_key
                self._try_init_sdk()

        if self._sdk_available and (self._client or self._genai) and self._api_key:
            return await self._generate_with_sdk(messages, model_name, start)
        else:
            return await self._generate_with_rest(messages, model_name, start)

    async def _generate_with_sdk(
        self, messages: List[LLMMessage], model_name: str, start: float
    ) -> LLMResponse:
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._sync_sdk_call, messages, model_name
            )
            elapsed = (time.time() - start) * 1000
            return LLMResponse(
                content=result,
                finish_reason=FinishReason.STOP,
                latency_ms=elapsed,
                model_name=model_name,
            )
        except Exception as e:
            logger.warning(f"[GeminiProvider] SDK call failed: {e}. Fallback to local response.")
            return await self._generate_with_rest(messages, model_name, start)

    def _sync_sdk_call(self, messages: List[LLMMessage], model_name: str) -> str:
        """Gọi đồng bộ Gemini SDK trong executor."""
        if self._use_new_genai and self._client:
            contents = []
            for msg in messages:
                if msg.role != MessageRole.SYSTEM and msg.content:
                    contents.append(f"{msg.role.value}: {msg.content}")
            if not contents:
                contents = ["Xin chào"]
            res = self._client.models.generate_content(
                model=model_name,
                contents=contents,
            )
            return res.text or ""

        history = []
        system_instruction = None

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = msg.content
            elif msg.role == MessageRole.USER:
                history.append({"role": "user", "parts": [{"text": msg.content or ""}]})
            elif msg.role == MessageRole.ASSISTANT:
                history.append({"role": "model", "parts": [{"text": msg.content or ""}]})

        gen_model = self._genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=self._genai.GenerationConfig(
                temperature=self._temperature,
                max_output_tokens=self._max_output_tokens,
            ),
        )

        if history and history[-1]["role"] == "user":
            last_user = history[-1]["parts"][0]["text"]
            prior_history = history[:-1]
        else:
            last_user = ""
            prior_history = history

        chat = gen_model.start_chat(history=prior_history)
        response = chat.send_message(last_user)
        return response.text

    async def _generate_with_rest(
        self, messages: List[LLMMessage], model_name: str, start: float
    ) -> LLMResponse:
        """Pattern matching fallback khi không có API key hoặc API lỗi."""
        elapsed = (time.time() - start) * 1000
        # Bỏ qua repair prompt để lấy user prompt gốc
        user_content = ""
        for m in reversed(messages):
            if m.role == MessageRole.USER and not m.content.startswith("JSON bạn vừa sinh ra"):
                user_content = m.content
                break
        if not user_content:
            user_content = next((m.content for m in reversed(messages) if m.role == MessageRole.USER), "")

        content = self._simple_fallback_response(user_content or "")
        return LLMResponse(
            content=content,
            finish_reason=FinishReason.STOP,
            latency_ms=elapsed,
            model_name=f"{model_name}-fallback",
        )

    def _simple_fallback_response(self, user_input: str) -> str:
        """
        Pattern-based fallback khi Gemini API chưa được kết nối hoặc phản hồi chậm.
        """
        lower = user_input.lower().strip()

        # Scolding / Apology patterns
        scolding_words = {"ngu", "dở", "dốt", "kém", "tệ", "gà", "bậy"}
        if any(w in lower for w in scolding_words):
            return "Em xin lỗi Sếp ạ! Em sẽ rút kinh nghiệm và tiếp tục hoàn thiện để hỗ trợ Sếp tốt hơn ạ."

        # Time query patterns
        if any(w in lower for w in ("mấy giờ", "thời gian")):
            from datetime import datetime
            now_str = datetime.now().strftime("%H:%M:%S, ngày %d/%m/%Y")
            return f"Bây giờ là {now_str} ạ Sếp!"

        # Greeting patterns
        greetings = {"hi", "hello", "chào", "alo", "xin chào", "hey", "chào tao đi", "chào tao"}
        if any(g in lower for g in greetings) and len(lower) < 25:
            return "Xin chào Sếp! Em là Eric, trợ lý AI của Sếp trên Windows. Em có thể giúp gì cho Sếp hôm nay ạ?"

        # Application & Web patterns
        app_patterns = {
            "notepad": ("launch_application", {"application": "notepad"}, ["desktop"]),
            "note": ("launch_application", {"application": "notepad"}, ["desktop"]),
            "ghi chú": ("launch_application", {"application": "notepad"}, ["desktop"]),
            "calc": ("launch_application", {"application": "calc"}, ["desktop"]),
            "máy tính": ("launch_application", {"application": "calc"}, ["desktop"]),
            "word": ("launch_application", {"application": "winword"}, ["desktop"]),
            "excel": ("launch_application", {"application": "excel"}, ["desktop"]),
            "chrome": ("launch_application", {"application": "chrome"}, ["desktop", "browser"]),
            "chorm": ("launch_application", {"application": "chrome"}, ["desktop", "browser"]),
            "chorme": ("launch_application", {"application": "chrome"}, ["desktop", "browser"]),
            "chrom": ("launch_application", {"application": "chrome"}, ["desktop", "browser"]),
            "vscode": ("launch_application", {"application": "code"}, ["desktop"]),
            "explorer": ("launch_application", {"application": "explorer"}, ["desktop"]),
            "youtube": ("navigate_web", {"url": "https://www.youtube.com"}, ["browser"]),
        }
        for keyword, (intent, params, caps) in app_patterns.items():
            if keyword in lower:
                return json.dumps({
                    "response_type": "agent",
                    "intent": intent,
                    "parameters": params,
                    "capability_requirements": caps,
                    "expected_result": {"description": f"Đã mở {keyword}"},
                    "reasoning": f"Người dùng muốn {intent} {keyword}",
                    "confidence": 0.95,
                }, ensure_ascii=False)

        # Web search patterns
        search_triggers = ["tìm kiếm", "search", "google", "tìm"]
        if any(t in lower for t in search_triggers):
            query = lower
            for t in search_triggers:
                query = query.replace(t, "").strip()
            return json.dumps({
                "response_type": "agent",
                "intent": "web_search",
                "parameters": {"query": query, "engine": "google"},
                "capability_requirements": ["browser"],
                "expected_result": {"description": f"Kết quả tìm kiếm cho '{query}'"},
                "reasoning": "Người dùng muốn tìm kiếm thông tin",
                "confidence": 0.90,
            }, ensure_ascii=False)

        # Default natural text response (không trả JSON thô ra màn hình)
        return "Dạ Sếp! Em luôn sẵn sàng hỗ trợ Sếp trên hệ thống. Sếp cần em mở ứng dụng hay xử lý tác vụ gì ạ?"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key) or self._sdk_available
