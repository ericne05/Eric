"""
app/persistence/interfaces.py — Session Persistence Interfaces.

Defines the abstract repository contract for durable session storage.
Dependency direction: app/persistence → core (data models only).
app/persistence MUST NOT depend on UI/presentation code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.services.session_manager import ChatMessage, ChatSession


class ISessionRepository(ABC):
    """
    Abstract repository for durable chat session persistence.

    Implementations MUST be safe to call from any thread (single-threaded
    asyncio loop assumed; no additional locking required for SQLite).
    """

    # ── Session CRUD ──────────────────────────────────────────────────

    @abstractmethod
    def create_session(self, session: ChatSession) -> None:
        """Persist a newly created session (metadata only, no messages)."""

    @abstractmethod
    def update_session(self, session: ChatSession) -> None:
        """Persist updated session metadata (title, is_pinned, updated_at)."""

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages (cascade)."""

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Load a single session by ID (messages NOT loaded)."""

    @abstractmethod
    def list_sessions(self) -> List[ChatSession]:
        """
        Load all sessions ordered by: pinned first, then updated_at descending.
        Messages are NOT loaded — call get_messages() separately.
        """

    # ── Message CRUD ──────────────────────────────────────────────────

    @abstractmethod
    def add_message(self, session_id: str, msg: ChatMessage) -> None:
        """Append a message to an existing session."""

    @abstractmethod
    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """Load all messages for a session in insertion order."""

    # ── Last Session ──────────────────────────────────────────────────

    @abstractmethod
    def get_last_session_id(self) -> Optional[str]:
        """Return the ID of the session that was last active (or None)."""

    @abstractmethod
    def set_last_session_id(self, session_id: str) -> None:
        """Persist the ID of the currently active session."""

    # ── Goal State (transport-safe summary only) ──────────────────────

    @abstractmethod
    def save_goal_state(
        self,
        goal_id: str,
        session_id: Optional[str],
        title: str,
        intent: str,
        state: str,
        result_json: Optional[str],
    ) -> None:
        """
        Persist transport-safe goal state fields.

        MUST NOT serialize live runtime objects (EventBus, adapters,
        coroutines, ExecutionPlan steps, DAG, callbacks, or tasks).
        Only primitive/enum/JSON-serializable summary fields allowed.
        """

    @abstractmethod
    def load_goal_states(self, session_id: str) -> List[Dict]:
        """
        Load all persisted goal states for a session.

        Returns a list of dicts with keys:
            goal_id, session_id, title, intent, state, result_json,
            created_at, updated_at
        """

    @abstractmethod
    def normalize_interrupted_goals(self) -> int:
        """
        Normalize all goals stored with an active (non-terminal) state to
        'interrupted'. Called once during startup after an unclean shutdown.

        Terminal states (completed, failed, cancelled, interrupted) are
        left unchanged.

        Returns the count of goals that were normalized.
        """
