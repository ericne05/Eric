"""
core/chat — Chat Conversation Layer.

Quản lý lịch sử hội thoại giữa người dùng và Eric.
Tách biệt hoàn toàn với LLM Provider và Goal System.
"""

from core.chat.models import (
    ChatMessage,
    ChatRole,
    IntentType,
    IntentClassification,
    ParsedGoalSpec,
    ExecutionResult,
)
from core.chat.conversation import Conversation
from core.chat.history import HistoryManager

__all__ = [
    "ChatMessage",
    "ChatRole",
    "IntentType",
    "IntentClassification",
    "ParsedGoalSpec",
    "ExecutionResult",
    "Conversation",
    "HistoryManager",
]
