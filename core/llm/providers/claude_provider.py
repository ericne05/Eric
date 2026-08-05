"""
core/llm/providers/claude_provider.py — Anthropic Claude LLM Provider Stub.
Ready for integration — cần cấu hình ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

from core.llm.interfaces import ILLMProvider
from core.llm.models import LLMMessage, LLMResponse, ModelConfig
from core.llm.enums import FinishReason, MessageRole


class ClaudeProvider(ILLMProvider):
    """Anthropic Claude Provider (claude-3-5-sonnet, claude-3-haiku, etc.)."""

    DEFAULT_MODEL = "claude-3-5-haiku-20241022"

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model_name = model_name
        self._client = None
        self._try_init()

    def _try_init(self) -> None:
        try:
            import anthropic  # type: ignore
            if self._api_key:
                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
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
                content="[Claude] Provider chưa được cấu hình. Vui lòng thiết lập ANTHROPIC_API_KEY.",
                finish_reason=FinishReason.ERROR,
                latency_ms=(time.time() - start) * 1000,
                model_name=self._model_name,
            )

        system_content = ""
        claude_messages = []
        for m in messages:
            if m.role == MessageRole.SYSTEM:
                system_content = m.content or ""
            elif m.role == MessageRole.USER:
                claude_messages.append({"role": "user", "content": m.content or ""})
            elif m.role == MessageRole.ASSISTANT:
                claude_messages.append({"role": "assistant", "content": m.content or ""})

        response = await self._client.messages.create(
            model=model.name if model else self._model_name,
            system=system_content,
            messages=claude_messages,
            max_tokens=2048,
        )
        content = response.content[0].text if response.content else ""
        return LLMResponse(
            content=content,
            finish_reason=FinishReason.STOP,
            latency_ms=(time.time() - start) * 1000,
            model_name=self._model_name,
        )

    @property
    def is_available(self) -> bool:
        return bool(self._api_key) and self._client is not None
