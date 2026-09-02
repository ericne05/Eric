"""
Session Manager.
Manages chat sessions: New Chat, Conversation History, Restore Last Session, Pinned Conversations.
"""

from dataclasses import dataclass, field
import datetime
from typing import Dict, List, Optional
import uuid


@dataclass
class ChatMessage:
    """Represents a single message in a Chat Session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = "user"  # 'user', 'eric', 'system'
    content: str = ""
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    status_indicator: str = "completed"  # 'thinking', 'planning', 'executing', 'completed', 'failed'


@dataclass
class ChatSession:
    """Represents a persistent Chat Session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    messages: List[ChatMessage] = field(default_factory=list)
    is_pinned: bool = False
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class SessionManager:
    """
    Manages persistent Chat Sessions across App restarts.
    """

    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}
        self._active_session_id: Optional[str] = None

    def create_session(self, title: str = "New Conversation") -> ChatSession:
        session = ChatSession(title=title)
        self._sessions[session.id] = session
        self._active_session_id = session.id
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def get_active_session(self) -> ChatSession:
        if not self._active_session_id or self._active_session_id not in self._sessions:
            return self.create_session()
        return self._sessions[self._active_session_id]

    def add_message(self, content: str, sender: str = "user", status: str = "completed") -> ChatMessage:
        session = self.get_active_session()
        msg = ChatMessage(sender=sender, content=content, status_indicator=status)
        session.messages.append(msg)
        session.updated_at = datetime.datetime.now(datetime.timezone.utc)
        if len(session.messages) == 1 and sender == "user":
            session.title = content[:30] + ("..." if len(content) > 30 else "")
        return msg

    def restore_last_session(self) -> Optional[ChatSession]:
        if not self._sessions:
            return self.create_session("Restored Session")
        last = max(self._sessions.values(), key=lambda s: s.updated_at)
        self._active_session_id = last.id
        return last

    def pin_session(self, session_id: str, is_pinned: bool = True) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.is_pinned = is_pinned
            return True
        return False

    def list_sessions(self) -> List[ChatSession]:
        return sorted(self._sessions.values(), key=lambda s: (not s.is_pinned, s.updated_at), reverse=True)
