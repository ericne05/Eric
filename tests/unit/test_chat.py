"""
tests/unit/test_chat.py — Unit Tests for core/chat module.
"""

import pytest
from core.chat.models import (
    ChatMessage, ChatRole, IntentType, IntentClassification,
    ParsedGoalSpec, ExecutionResult
)
from core.chat.conversation import Conversation
from core.chat.history import HistoryManager
from core.chat.intent_classifier import IntentClassifier
from core.chat.goal_parser import GoalParser


class TestChatModels:
    def test_chat_message_user_factory(self):
        msg = ChatMessage.user("Mở Notepad")
        assert msg.role == ChatRole.USER
        assert msg.content == "Mở Notepad"
        assert msg.id is not None

    def test_chat_message_assistant_factory(self):
        msg = ChatMessage.assistant("Đã mở Notepad", metadata={"intent": "launch_application"})
        assert msg.role == ChatRole.ASSISTANT
        assert msg.metadata["intent"] == "launch_application"

    def test_parsed_goal_spec_valid(self):
        spec = ParsedGoalSpec(
            intent="launch_application",
            parameters={"application": "notepad"},
            capability_requirements=["desktop"],
            confidence=0.98,
        )
        assert spec.is_valid()
        assert spec.requires_desktop()
        assert not spec.requires_browser()

    def test_parsed_goal_spec_invalid_empty_intent(self):
        spec = ParsedGoalSpec(intent="")
        assert not spec.is_valid()

    def test_execution_result_success_summary(self):
        result = ExecutionResult(
            success=True,
            runtime="desktop",
            intent="launch_application",
            duration_ms=342.0,
        )
        summary = result.to_summary()
        assert "thành công" in summary
        assert "desktop" in summary

    def test_execution_result_failure_summary(self):
        result = ExecutionResult(
            success=False,
            runtime="desktop",
            intent="launch_application",
            error="Process not found",
        )
        summary = result.to_summary()
        assert "thất bại" in summary
        assert "Process not found" in summary


class TestConversation:
    def test_add_and_get_messages(self):
        conv = Conversation()
        conv.add_user_message("Mở Notepad")
        conv.add_assistant_message("Đã mở Notepad")
        history = conv.get_history()
        assert len(history) == 2
        assert history[0].role == ChatRole.USER
        assert history[1].role == ChatRole.ASSISTANT

    def test_turn_count(self):
        conv = Conversation()
        conv.add_user_message("hi")
        conv.add_assistant_message("hello")
        conv.add_user_message("Mở Chrome")
        assert conv.turn_count == 2

    def test_clear_preserves_system_message(self):
        conv = Conversation()
        conv.add_system_message("System prompt")
        conv.add_user_message("Mở Notepad")
        conv.clear()
        history = conv.get_history()
        assert len(history) == 1
        assert history[0].role == ChatRole.SYSTEM

    def test_get_last_user_message(self):
        conv = Conversation()
        conv.add_user_message("first")
        conv.add_user_message("last")
        last = conv.get_last_user_message()
        assert last.content == "last"


class TestIntentClassifier:
    def setup_method(self):
        self.clf = IntentClassifier()

    def test_greeting_is_chat(self):
        result = self.clf.classify("hi")
        assert result.intent == IntentType.CHAT
        assert result.requires_llm is False

    def test_chao_is_chat(self):
        result = self.clf.classify("chào")
        assert result.intent == IntentType.CHAT

    def test_open_notepad_is_agent(self):
        result = self.clf.classify("mở Notepad")
        assert result.intent == IntentType.AGENT
        assert result.requires_runtime is True

    def test_open_chrome_is_agent(self):
        result = self.clf.classify("mở Chrome")
        assert result.intent == IntentType.AGENT

    def test_what_is_question(self):
        result = self.clf.classify("Notepad là gì?")
        assert result.intent == IntentType.QUESTION
        assert result.requires_runtime is False

    def test_remember_is_memory(self):
        result = self.clf.classify("nhớ rằng tôi thích dark mode")
        assert result.intent == IntentType.MEMORY_UPDATE

    def test_cam_on_is_chat(self):
        result = self.clf.classify("cảm ơn")
        assert result.intent == IntentType.CHAT


class TestGoalParser:
    def setup_method(self):
        self.parser = GoalParser()

    def test_parse_valid_json(self):
        raw = '{"intent": "launch_application", "parameters": {"application": "notepad"}, "capability_requirements": ["desktop"], "confidence": 0.98, "reasoning": "Mở notepad", "priority": "normal", "expected_result": {"description": "Notepad mở"}}'
        spec = self.parser.parse(raw)
        assert spec is not None
        assert spec.intent == "launch_application"
        assert spec.parameters["application"] == "notepad"
        assert spec.requires_desktop()
        assert spec.confidence == 0.98

    def test_parse_json_in_markdown_block(self):
        raw = '```json\n{"intent": "web_search", "parameters": {"query": "ChatGPT"}, "capability_requirements": ["browser"], "confidence": 0.9, "reasoning": "search", "priority": "normal", "expected_result": {}}\n```'
        spec = self.parser.parse(raw)
        assert spec is not None
        assert spec.intent == "web_search"
        assert spec.requires_browser()

    def test_parse_invalid_json_returns_none(self):
        spec = self.parser.parse("{invalid json}")
        assert spec is None

    def test_parse_empty_returns_none(self):
        spec = self.parser.parse("")
        assert spec is None

    def test_parse_missing_intent_returns_none(self):
        raw = '{"parameters": {}, "capability_requirements": []}'
        spec = self.parser.parse(raw)
        assert spec is None

    def test_chat_response_detection(self):
        assert self.parser.is_chat_response("Xin chào! Tôi là Eric.") is True
        assert self.parser.is_chat_response('{"intent": "launch_application"}') is False
