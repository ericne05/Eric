"""
core/llm/router.py — LLM Router with Provider Capability Negotiation.

Tự động chọn LLM Provider phù hợp (Gemini -> OpenAI -> Claude -> Fallback).
Sau này thêm provider mới (Ollama, vLLM, Azure...) không cần sửa Router.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from core.llm.interfaces import ILLMProvider
from core.llm.models import LLMMessage, LLMResponse, ModelConfig
from core.llm.enums import FinishReason

logger = logging.getLogger(__name__)


class ProviderEntry:
    """Một provider được đăng ký trong Router kèm metadata."""
    def __init__(
        self,
        name: str,
        provider: ILLMProvider,
        priority: int = 100,
        capabilities: Optional[List[str]] = None,
    ):
        self.name = name
        self.provider = provider
        self.priority = priority  # Số nhỏ hơn = ưu tiên cao hơn
        self.capabilities = capabilities or ["chat", "goal"]
        self.failure_count = 0
        self.max_failures = 3


class LLMRouter:
    """
    Router điều phối LLM Providers.

    Kiến trúc mở rộng — thêm provider bằng register(), không sửa Router:
    
    LLMRouter
    ├── GeminiProvider  (priority=10)
    ├── OpenAIProvider  (priority=20)
    ├── ClaudeProvider  (priority=30)
    ├── OllamaProvider  (priority=50)  ← thêm sau
    └── ...
    """

    def __init__(self):
        self._providers: List[ProviderEntry] = []

    def register(
        self,
        name: str,
        provider: ILLMProvider,
        priority: int = 100,
        capabilities: Optional[List[str]] = None,
    ) -> "LLMRouter":
        """Đăng ký một provider. Có thể chain: router.register(...).register(...)"""
        entry = ProviderEntry(name, provider, priority, capabilities)
        self._providers.append(entry)
        self._providers.sort(key=lambda e: e.priority)
        logger.info(f"[LLMRouter] Registered provider '{name}' (priority={priority})")
        return self

    def get_available_providers(self) -> List[ProviderEntry]:
        return [
            e for e in self._providers
            if e.failure_count < e.max_failures
        ]

    async def chat(
        self,
        messages: List[LLMMessage],
        required_capability: str = "chat",
        model: Optional[ModelConfig] = None,
        cancellation_token=None,
    ) -> LLMResponse:
        """
        Gửi messages đến provider phù hợp nhất.
        Nếu thất bại, tự động failover sang provider tiếp theo.
        """
        candidates = [
            e for e in self.get_available_providers()
            if required_capability in e.capabilities
        ]

        if not candidates:
            return LLMResponse(
                content="[LLMRouter] Không có LLM Provider nào khả dụng.",
                finish_reason=FinishReason.ERROR,
            )

        last_error: Optional[str] = None
        for entry in candidates:
            try:
                logger.debug(f"[LLMRouter] Thử provider '{entry.name}'...")
                response = await entry.provider.generate(
                    messages=messages,
                    model=model,
                    cancellation_token=cancellation_token,
                )
                if response.finish_reason != FinishReason.ERROR:
                    entry.failure_count = 0  # Reset nếu thành công
                    logger.debug(f"[LLMRouter] Provider '{entry.name}' thành công.")
                    return response
                else:
                    entry.failure_count += 1
                    last_error = response.content
                    logger.warning(f"[LLMRouter] Provider '{entry.name}' lỗi — thử tiếp...")
            except Exception as e:
                entry.failure_count += 1
                last_error = str(e)
                logger.warning(f"[LLMRouter] Provider '{entry.name}' exception: {e}")

        return LLMResponse(
            content=f"[LLMRouter] Tất cả providers thất bại. Lỗi cuối: {last_error}",
            finish_reason=FinishReason.ERROR,
        )

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    def status(self) -> Dict[str, Any]:
        return {
            "providers": [
                {
                    "name": e.name,
                    "priority": e.priority,
                    "capabilities": e.capabilities,
                    "failures": e.failure_count,
                    "available": e.failure_count < e.max_failures,
                }
                for e in self._providers
            ]
        }


def build_default_router() -> LLMRouter:
    """
    Tạo LLMRouter mặc định với các providers chuẩn.
    Thứ tự ưu tiên: Gemini -> OpenAI -> Claude.
    """
    from core.llm.providers.gemini import GeminiProvider
    from core.llm.providers.openai_provider import OpenAIProvider
    from core.llm.providers.claude_provider import ClaudeProvider

    router = LLMRouter()
    router.register("gemini", GeminiProvider(), priority=10, capabilities=["chat", "goal"])
    router.register("openai", OpenAIProvider(), priority=20, capabilities=["chat", "goal"])
    router.register("claude", ClaudeProvider(), priority=30, capabilities=["chat", "goal"])
    return router
