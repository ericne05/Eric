"""
tests/integration/test_chat_llm_goal_pipeline.py
E2E Integration Test — Luồng: Chat -> IntentClassifier -> GeminiProvider(fallback) -> GoalParser -> GoalManager -> ExecutionResult.
Use-case đầu tiên: "Mở Notepad" (không cần Internet, không cần Browser).
"""

import pytest
import asyncio

from core.chat.models import IntentType, ParsedGoalSpec, ExecutionResult
from core.chat.conversation import Conversation
from core.chat.intent_classifier import IntentClassifier
from core.chat.goal_parser import GoalParser
from core.llm.providers.gemini import GeminiProvider
from core.llm.router import LLMRouter, build_default_router
from core.llm.prompts import PromptBuilder
from core.llm.enums import MessageRole
from core.llm.models import LLMMessage


@pytest.mark.asyncio
async def test_intent_classifier_notepad_is_agent():
    """Phân loại 'mở Notepad' phải là AGENT."""
    clf = IntentClassifier()
    result = clf.classify("mở Notepad")
    assert result.intent == IntentType.AGENT
    assert result.requires_runtime is True
    assert result.requires_llm is True


@pytest.mark.asyncio
async def test_gemini_provider_fallback_notepad():
    """GeminiProvider fallback (không cần API key) sinh GoalSpec JSON hợp lệ cho 'mở Notepad'."""
    provider = GeminiProvider(api_key="")  # fallback mode
    messages = PromptBuilder.build_agent_request("mở Notepad")
    response = await provider.generate(messages)
    assert response.content is not None
    # Fallback phải trả về JSON với intent launch_application
    parser = GoalParser()
    spec = parser.parse(response.content)
    assert spec is not None
    assert spec.intent == "launch_application"
    assert "notepad" in spec.parameters.get("application", "").lower()
    assert spec.requires_desktop()


@pytest.mark.asyncio
async def test_llm_router_notepad_goal_spec():
    """LLMRouter sinh GoalSpec hợp lệ cho 'mở Notepad'."""
    router = build_default_router()
    messages = PromptBuilder.build_agent_request("mở Notepad")
    response = await router.chat(messages, required_capability="goal")
    assert response.content is not None
    parser = GoalParser()
    spec = parser.parse(response.content)
    assert spec is not None
    assert spec.is_valid()
    assert spec.intent == "launch_application"


@pytest.mark.asyncio
async def test_goal_parser_web_search():
    """GoalParser parse đúng web_search spec."""
    import json
    raw = json.dumps({
        "intent": "web_search",
        "parameters": {"query": "ChatGPT", "engine": "google"},
        "capability_requirements": ["browser"],
        "constraints": {},
        "priority": "normal",
        "expected_result": {"description": "Kết quả tìm kiếm ChatGPT"},
        "reasoning": "Người dùng muốn tìm kiếm",
        "confidence": 0.95,
    }, ensure_ascii=False)
    parser = GoalParser()
    spec = parser.parse(raw)
    assert spec is not None
    assert spec.intent == "web_search"
    assert spec.parameters["query"] == "ChatGPT"
    assert spec.requires_browser()
    assert not spec.requires_desktop()


@pytest.mark.asyncio
async def test_full_pipeline_open_notepad():
    """
    E2E Test — Luồng đầy đủ cho 'Mở Notepad':
    IntentClassifier -> GeminiProvider(fallback) -> GoalParser -> ParsedGoalSpec
    """
    user_input = "mở Notepad"

    # Bước 1: Intent Classification
    clf = IntentClassifier()
    intent = clf.classify(user_input)
    assert intent.intent == IntentType.AGENT
    assert intent.requires_runtime is True

    # Bước 2: LLM sinh GoalSpec
    router = build_default_router()
    messages = PromptBuilder.build_agent_request(user_input)
    llm_response = await router.chat(messages, required_capability="goal")
    assert llm_response.content is not None

    # Bước 3: Parse GoalSpec
    parser = GoalParser()
    spec = parser.parse(llm_response.content)
    assert spec is not None
    assert spec.is_valid()

    # Bước 4: Validate GoalSpec đúng ý định
    assert spec.intent == "launch_application"
    assert spec.requires_desktop()
    assert "notepad" in str(spec.parameters).lower()

    # Bước 5: ExecutionResult structure (mock runtime)
    result = ExecutionResult(
        success=True,
        runtime="desktop",
        intent=spec.intent,
        duration_ms=250.0,
        logs=["notepad.exe process started"],
        output_data={"pid": 12345},
    )
    assert result.success
    assert "thành công" in result.to_summary()


@pytest.mark.asyncio
async def test_greeting_fast_path_no_llm():
    """
    'Xin chào' phải được xử lý bằng fast-path (không cần gọi LLM).
    """
    clf = IntentClassifier()
    result = clf.classify("xin chào")
    assert result.intent == IntentType.CHAT
    assert result.requires_llm is False
    assert result.requires_runtime is False


@pytest.mark.asyncio
async def test_response_synthesis_prompt_structure():
    """PromptBuilder tạo đúng cấu trúc prompt cho response synthesis."""
    messages = PromptBuilder.build_response_synthesis(
        "mở Notepad",
        "Thực thi thành công: intent='launch_application' | runtime='desktop' | thời gian=250ms"
    )
    assert len(messages) == 2
    assert messages[0].role == MessageRole.SYSTEM
    assert messages[1].role == MessageRole.USER
    assert "mở Notepad" in messages[1].content
