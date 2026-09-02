from core.agents.models import CancellationToken
"""
LLM Service Implementation.
"""

import asyncio
from typing import List

from core.logger.interface import ILogger
from core.llm.enums import FinishReason
from core.llm.interfaces import ILLMProvider, ILLMService, IModelRegistry, ITokenBudgetManager
from core.llm.models import LLMMessage, LLMResponse
from core.telemetry.interfaces import ITelemetryManager
from core.tools.models import ToolSchema


class LLMService(ILLMService):
    def __init__(
        self,
        provider: ILLMProvider,
        model_registry: IModelRegistry,
        budget_manager: ITokenBudgetManager,
        telemetry: ITelemetryManager,
        logger: ILogger
    ):
        self._provider = provider
        self._registry = model_registry
        self._budget_manager = budget_manager
        self._telemetry = telemetry
        self._logger = logger

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[ToolSchema] | None = None,
        cancellation_token: CancellationToken | None = None,
        stream: bool = False
    ) -> LLMResponse:
        
        # Determine model
        model = self._registry.get_default_model()
        
        # Generate with simple retry mechanism
        retries = 3
        last_exception = None
        
        for attempt in range(retries):
            if cancellation_token and cancellation_token.is_cancelled:
                self._logger.warning(f"[LLMService] Request cancelled: {cancellation_token.reason}")
                return LLMResponse(finish_reason=FinishReason.ERROR, error_message=cancellation_token.reason)

            try:
                # Call Provider
                response = await self._provider.generate(
                    messages=messages,
                    tools=tools,
                    model=model,
                    cancellation_token=cancellation_token,
                    stream=stream
                )
                
                # Check budget if token usage is reported
                total_tokens = sum(response.token_usage.values())
                if total_tokens > 0:
                    self._telemetry.record_metric("llm_tokens", total_tokens, tags={"model": model.name})
                    # Thread ID could be passed, but for now we'll assume a global 'default' or get it from context later.
                    self._budget_manager.record_usage("default", total_tokens)
                    if not self._budget_manager.check_budget("default"):
                        self._logger.error("[LLMService] Token budget exceeded!")
                        return LLMResponse(finish_reason=FinishReason.ERROR)
                        
                return response
                
            except Exception as e:
                last_exception = e
                self._logger.warning(f"[LLMService] Provider error (attempt {attempt+1}/{retries}): {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        self._logger.error(f"[LLMService] Failed to generate after {retries} attempts.")
        return LLMResponse(finish_reason=FinishReason.ERROR)
