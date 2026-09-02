"""
LLM Service Implementation.

LLMService is a thin facade that handles:
- Budget tracking
- Telemetry recording
- Cancellation checks

Routing, provider selection, and failover are exclusively owned by LLMRouter.
LLMService MUST NOT select providers or implement its own failover.
"""

import asyncio
from typing import List, Optional

from core.logger.interface import ILogger
from core.llm.enums import FinishReason
from core.llm.interfaces import ILLMService, IModelRegistry, ITokenBudgetManager
from core.llm.models import LLMMessage, LLMResponse
from core.llm.router import LLMRouter
from core.telemetry.interfaces import ITelemetryManager
from core.tools.models import ToolSchema


class LLMService(ILLMService):
    """
    LLM Service facade.

    Delegates all provider calls and failover to LLMRouter.
    LLMRouter is the ONLY routing authority.
    """

    def __init__(
        self,
        router: LLMRouter,
        model_registry: IModelRegistry,
        budget_manager: ITokenBudgetManager,
        telemetry: ITelemetryManager,
        logger: ILogger,
    ):
        self._router = router
        self._registry = model_registry
        self._budget_manager = budget_manager
        self._telemetry = telemetry
        self._logger = logger

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSchema]] = None,
        cancellation_token=None,
        stream: bool = False,
    ) -> LLMResponse:
        # Check cancellation before starting
        if cancellation_token and cancellation_token.is_cancelled:
            self._logger.warning(
                f"[LLMService] Request cancelled: {cancellation_token.reason}"
            )
            return LLMResponse(
                content=f"Cancelled: {cancellation_token.reason}",
                finish_reason=FinishReason.ERROR,
            )

        # Check budget
        if not self._budget_manager.check_budget("default"):
            self._logger.error("[LLMService] Token budget exceeded before request.")
            return LLMResponse(finish_reason=FinishReason.ERROR)

        # Determine model from registry for metadata / telemetry
        model = self._registry.get_default_model()

        # Delegate routing + failover exclusively to LLMRouter
        response = await self._router.chat(
            messages=messages,
            required_capability="chat",
            model=model,
            cancellation_token=cancellation_token,
        )

        # Record telemetry if token usage is reported
        total_tokens = sum(response.token_usage.values()) if response.token_usage else 0
        if total_tokens > 0:
            self._telemetry.record_metric(
                "llm_tokens", total_tokens, tags={"model": model.name}
            )
            self._budget_manager.record_usage("default", total_tokens)
            if not self._budget_manager.check_budget("default"):
                self._logger.error("[LLMService] Token budget exceeded after request.")
                return LLMResponse(finish_reason=FinishReason.ERROR)

        return response
