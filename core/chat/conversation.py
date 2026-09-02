"""
core/chat/conversation.py — Conversation Manager.

Quản lý lịch sử hội thoại của một phiên làm việc.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from core.chat.models import ChatMessage, ChatRole


class Conversation:
    """
    Quản lý một cuộc hội thoại đơn lẻ.
    Lưu trữ lịch sử tin nhắn, hỗ trợ thêm và truy vấn.
    """

    def __init__(self, session_id: Optional[str] = None, max_history: int = 50):
        self.id = session_id or str(uuid.uuid4())
        self._messages: List[ChatMessage] = []
        self._max_history = max_history

    def add_user_message(self, content: str) -> ChatMessage:
        msg = ChatMessage.user(content)
        self._add(msg)
        return msg

    def add_assistant_message(self, content: str, metadata: Optional[dict] = None) -> ChatMessage:
        msg = ChatMessage.assistant(content, metadata=metadata)
        self._add(msg)
        return msg

    def add_system_message(self, content: str) -> ChatMessage:
        msg = ChatMessage.system(content)
        self._add(msg)
        return msg

    def _add(self, msg: ChatMessage) -> None:
        self._messages.append(msg)
        # Giữ max_history tin nhắn gần nhất (bỏ qua system message đầu tiên)
        non_system = [m for m in self._messages if m.role != ChatRole.SYSTEM]
        if len(non_system) > self._max_history:
            # Xóa tin nhắn cũ nhất (không phải system)
            oldest = next(m for m in self._messages if m.role != ChatRole.SYSTEM)
            self._messages.remove(oldest)

    def get_history(self, include_system: bool = True) -> List[ChatMessage]:
        if include_system:
            return list(self._messages)
        return [m for m in self._messages if m.role != ChatRole.SYSTEM]

    def get_last_user_message(self) -> Optional[ChatMessage]:
        for msg in reversed(self._messages):
            if msg.role == ChatRole.USER:
                return msg
        return None

    def get_last_assistant_message(self) -> Optional[ChatMessage]:
        for msg in reversed(self._messages):
            if msg.role == ChatRole.ASSISTANT:
                return msg
        return None

    def clear(self) -> None:
        """Xóa toàn bộ lịch sử, giữ lại system message đầu tiên nếu có."""
        system_msgs = [m for m in self._messages if m.role == ChatRole.SYSTEM]
        self._messages = system_msgs

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def turn_count(self) -> int:
        """Số lượt hội thoại (mỗi lượt = 1 user + 1 assistant)."""
        user_msgs = sum(1 for m in self._messages if m.role == ChatRole.USER)
        return user_msgs

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "messages": [m.to_dict() for m in self._messages],
            "message_count": self.message_count,
            "turn_count": self.turn_count,
        }
