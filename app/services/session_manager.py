"""
Session Manager.
Manages chat sessions: New Chat, Conversation History, Restore Last Session, Pinned Conversations.

Persistence is optional: if an ISessionRepository is injected, all mutations are durably
written to the repository. If no repository is provided (e.g. unit tests without DI), the
SessionManager operates identically to the original pure in-memory mode.
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

    When a repository is provided, all session mutations are durably persisted.
    On construction with a repository, existing sessions are loaded from storage
    so the in-memory dict reflects the last saved state.

    If repository is None, operates as a pure in-memory store (identical to
    the original behaviour — no persistence, no schema, no I/O).
    """

    def __init__(self, repository=None):
        """
        Args:
            repository: Optional ISessionRepository for durable persistence.
                        If None, sessions are in-memory only (no disk I/O).
        """
        self._sessions: Dict[str, ChatSession] = {}
        self._active_session_id: Optional[str] = None
        self._repo = repository

        if self._repo is not None:
            self._load_from_repo()

    # ── Public API ────────────────────────────────────────────────────

    def create_session(self, title: str = "New Conversation") -> ChatSession:
        session = ChatSession(title=title)
        self._sessions[session.id] = session
        self._active_session_id = session.id
        if self._repo is not None:
            self._repo.create_session(session)
            self._repo.set_last_session_id(session.id)
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
            if self._repo is not None:
                self._repo.update_session(session)
        if self._repo is not None:
            self._repo.add_message(session.id, msg)
            self._repo.update_session(session)
        return msg

    def restore_last_session(self) -> Optional[ChatSession]:
        # Prefer the repository's last-active session ID
        if self._repo is not None:
            last_id = self._repo.get_last_session_id()
            if last_id and last_id in self._sessions:
                self._active_session_id = last_id
                return self._sessions[last_id]

        # Fallback: most-recently-updated session in memory
        if not self._sessions:
            return self.create_session("Restored Session")
        last = max(self._sessions.values(), key=lambda s: s.updated_at)
        self._active_session_id = last.id
        if self._repo is not None:
            self._repo.set_last_session_id(last.id)
        return last

    def pin_session(self, session_id: str, is_pinned: bool = True) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.is_pinned = is_pinned
            if self._repo is not None:
                self._repo.update_session(session)
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory and (if available) the repository."""
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        if self._active_session_id == session_id:
            self._active_session_id = None
        if self._repo is not None:
            self._repo.delete_session(session_id)
        return True

    def list_sessions(self) -> List[ChatSession]:
        return sorted(self._sessions.values(), key=lambda s: (not s.is_pinned, s.updated_at), reverse=True)

    # ── Internal Helpers ──────────────────────────────────────────────

    def _load_from_repo(self) -> None:
        """Populate the in-memory dict from the repository on startup."""
        try:
            sessions = self._repo.list_sessions()
            for session in sessions:
                # Load messages for each session
                messages = self._repo.get_messages(session.id)
                session.messages = messages
                self._sessions[session.id] = session

            # Restore the last active session ID
            last_id = self._repo.get_last_session_id()
            if last_id and last_id in self._sessions:
                self._active_session_id = last_id
        except Exception:  # noqa: BLE001
            # Repository failure must not crash the app — fall through to empty state
            import logging
            logging.getLogger(__name__).warning(
                "[SessionManager] Failed to load sessions from repository; starting fresh."
            )
