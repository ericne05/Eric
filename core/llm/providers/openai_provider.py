"""
core/llm/providers/openai_provider.py — OpenAI LLM Provider Stub.
Ready for integration — cần cấu hình OPENAI_API_KEY.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

from core.llm.interfaces import ILLMProvider
from core.llm.models import LLMMessage, LLMResponse, ModelConfig
from core.llm.enums import FinishReason


class OpenAIProvider(ILLMProvider):
    """OpenAI GPT Provider (gpt-4o, gpt-4-turbo, etc.)."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model_name = model_name
        self._client = None
        self._try_init()

    def _try_init(self) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore
            if self._api_key:
                self._client = AsyncOpenAI(api_key=self._api_key)
        except ImportError:
            pass

    async def generate(
        self,
        messages: List[LLMMessage],
        tools=None,
        model: Optional[ModelConfig] = None,
        cancellation_token=None,
        stream: bool = False,
    ) -> LLMResponse:
        start = time.time()
        if not self._client or not self._api_key:
            return LLMResponse(
                content="[OpenAI] Provider chưa được cấu hình. Vui lòng thiết lập OPENAI_API_KEY.",
                finish_reason=FinishReason.ERROR,
                latency_ms=(time.time() - start) * 1000,
                model_name=self._model_name,
            )

        from core.llm.enums import MessageRole
        openai_messages = []
        for m in messages:
            role = "user" if m.role == MessageRole.USER else (
                "assistant" if m.role == MessageRole.ASSISTANT else "system"
            )
            openai_messages.append({"role": role, "content": m.content or ""})

        response = await self._client.chat.completions.create(
            model=model.name if model else self._model_name,
            messages=openai_messages,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(
            content=content,
            finish_reason=FinishReason.STOP,
            latency_ms=(time.time() - start) * 1000,
            model_name=self._model_name,
        )

    @property
    def is_available(self) -> bool:
        return bool(self._api_key) and self._client is not None
