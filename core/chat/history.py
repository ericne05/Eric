"""
core/chat/history.py — History Manager.

Lưu và khôi phục lịch sử hội thoại theo session.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from core.chat.conversation import Conversation
from core.chat.models import ChatMessage, ChatRole


class HistoryManager:
    """
    Quản lý nhiều Conversation theo session_id.
    Hỗ trợ lưu/khôi phục lịch sử từ %LOCALAPPDATA%\\Eric\\sessions.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self._conversations: Dict[str, Conversation] = {}

        if storage_dir is None:
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            storage_dir = os.path.join(appdata, "Eric", "sessions")
        self._storage_dir = storage_dir
        os.makedirs(self._storage_dir, exist_ok=True)

    def get_or_create(self, session_id: str, max_history: int = 50) -> Conversation:
        if session_id not in self._conversations:
            conv = Conversation(session_id=session_id, max_history=max_history)
            # Thử khôi phục từ file nếu có
            self._load_from_file(conv)
            self._conversations[session_id] = conv
        return self._conversations[session_id]

    def save(self, session_id: str) -> None:
        if session_id not in self._conversations:
            return
        conv = self._conversations[session_id]
        path = os.path.join(self._storage_dir, f"{session_id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(conv.to_dict(), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _load_from_file(self, conv: Conversation) -> None:
        path = os.path.join(self._storage_dir, f"{conv.id}.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for m in data.get("messages", []):
                role = ChatRole(m.get("role", "user"))
                content = m.get("content", "")
                if role == ChatRole.USER:
                    conv.add_user_message(content)
                elif role == ChatRole.ASSISTANT:
                    conv.add_assistant_message(content)
                elif role == ChatRole.SYSTEM:
                    conv.add_system_message(content)
        except (json.JSONDecodeError, OSError):
            pass

    def clear(self, session_id: str) -> None:
        if session_id in self._conversations:
            self._conversations[session_id].clear()

    def list_sessions(self) -> List[str]:
        return list(self._conversations.keys())
