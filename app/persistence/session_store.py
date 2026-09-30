"""
app/persistence/session_store.py — SQLite Session Store.

Durable SQLite-backed implementation of ISessionRepository.
Follows the same ILifecycleAware pattern established by LongTermMemory
and SQLiteKnowledgeGraphStore.

Database file: %LOCALAPPDATA%\\Eric\\sessions\\sessions.db
(path injected at construction time — tests use a tmp_path or :memory:)

Migration: on first initialize(), legacy HistoryManager JSON files found
in the sessions directory are imported idempotently using a metadata flag.
Original JSON files are NOT deleted.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from core.di.interfaces import ILifecycleAware

from app.persistence.interfaces import ISessionRepository
from app.services.session_manager import ChatMessage, ChatSession

logger = logging.getLogger(__name__)

# Goal states that are considered terminal (no normalization needed)
_TERMINAL_GOAL_STATES = frozenset({"completed", "failed", "cancelled", "interrupted"})


class SQLiteSessionStore(ISessionRepository, ILifecycleAware):
    """
    SQLite-backed durable session store.

    Schema:
        sessions  — session metadata (id, title, is_pinned, created_at, updated_at)
        messages  — chat messages in insertion order (session_id FK, seq)
        goal_states — transport-safe goal summaries (goal_id, session_id, state…)
        metadata  — key/value pairs (last_session_id, migration flags)

    Lifecycle:
        initialize() — connect, PRAGMA, create tables, run JSON migration
        dispose()    — close connection cleanly
    """

    _SCHEMA_SQL = """
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT 'New Conversation',
            is_pinned   INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id               TEXT PRIMARY KEY,
            session_id       TEXT NOT NULL,
            sender           TEXT NOT NULL,
            content          TEXT NOT NULL,
            timestamp        TEXT NOT NULL,
            status_indicator TEXT NOT NULL DEFAULT 'completed',
            seq              INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, seq);

        CREATE TABLE IF NOT EXISTS goal_states (
            goal_id     TEXT PRIMARY KEY,
            session_id  TEXT,
            title       TEXT NOT NULL DEFAULT '',
            intent      TEXT NOT NULL DEFAULT '',
            state       TEXT NOT NULL,
            result_json TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_goal_states_session
            ON goal_states(session_id);

        CREATE TABLE IF NOT EXISTS metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """

    def __init__(self, db_path: str) -> None:
        """
        Args:
            db_path: Absolute path to the SQLite database file.
                     Use ":memory:" for isolated unit tests.
        """
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ── ILifecycleAware ────────────────────────────────────────────────

    def initialize(self) -> None:
        """Connect, create schema, and run legacy JSON migration."""
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(self._SCHEMA_SQL)
        self._conn.commit()

        # Normalize any goals left in a non-terminal state from a previous run
        normalized = self.normalize_interrupted_goals()
        if normalized:
            logger.warning(
                "[SQLiteSessionStore] Normalized %d interrupted goal(s) on startup.",
                normalized,
            )

        # Migrate legacy JSON files if any exist
        self._migrate_legacy_json()

        logger.info("[SQLiteSessionStore] Initialized at %s", self._db_path)

    def dispose(self) -> None:
        """Close the SQLite connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("[SQLiteSessionStore] Connection closed.")

    # ── ISessionRepository — Session CRUD ─────────────────────────────

    def create_session(self, session: ChatSession) -> None:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO sessions (id, title, is_pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.title,
                    1 if session.is_pinned else 0,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                ),
            )

    def update_session(self, session: ChatSession) -> None:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        with self._conn:
            self._conn.execute(
                """
                UPDATE sessions
                SET title=?, is_pinned=?, updated_at=?
                WHERE id=?
                """,
                (
                    session.title,
                    1 if session.is_pinned else 0,
                    session.updated_at.isoformat(),
                    session.id,
                ),
            )

    def delete_session(self, session_id: str) -> None:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        with self._conn:
            self._conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        row = self._conn.execute(
            "SELECT id, title, is_pinned, created_at, updated_at FROM sessions WHERE id=?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def list_sessions(self) -> List[ChatSession]:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        rows = self._conn.execute(
            """
            SELECT id, title, is_pinned, created_at, updated_at
            FROM sessions
            ORDER BY is_pinned DESC, updated_at DESC
            """
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    # ── ISessionRepository — Message CRUD ─────────────────────────────

    def add_message(self, session_id: str, msg: ChatMessage) -> None:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        seq = self._next_seq(session_id)
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO messages
                    (id, session_id, sender, content, timestamp, status_indicator, seq)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg.id,
                    session_id,
                    msg.sender,
                    msg.content,
                    msg.timestamp.isoformat(),
                    msg.status_indicator,
                    seq,
                ),
            )

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        rows = self._conn.execute(
            """
            SELECT id, sender, content, timestamp, status_indicator
            FROM messages
            WHERE session_id=?
            ORDER BY seq ASC
            """,
            (session_id,),
        ).fetchall()
        return [self._row_to_message(r) for r in rows]

    # ── ISessionRepository — Last Session ─────────────────────────────

    def get_last_session_id(self) -> Optional[str]:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key='last_session_id'"
        ).fetchone()
        return row["value"] if row else None

    def set_last_session_id(self, session_id: str) -> None:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO metadata (key, value) VALUES ('last_session_id', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (session_id,),
            )

    # ── ISessionRepository — Goal State ───────────────────────────────

    def save_goal_state(
        self,
        goal_id: str,
        session_id: Optional[str],
        title: str,
        intent: str,
        state: str,
        result_json: Optional[str],
    ) -> None:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO goal_states
                    (goal_id, session_id, title, intent, state, result_json,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(goal_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    title=excluded.title,
                    intent=excluded.intent,
                    state=excluded.state,
                    result_json=excluded.result_json,
                    updated_at=excluded.updated_at
                """,
                (goal_id, session_id, title, intent, state, result_json, now, now),
            )

    def load_goal_states(self, session_id: str) -> List[Dict]:
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        rows = self._conn.execute(
            """
            SELECT goal_id, session_id, title, intent, state, result_json,
                   created_at, updated_at
            FROM goal_states
            WHERE session_id=?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def normalize_interrupted_goals(self) -> int:
        """
        Set any goal whose state is NOT terminal to 'interrupted'.
        Called once at startup to handle unclean shutdown survivors.
        """
        assert self._conn is not None, "SQLiteSessionStore not initialized"
        # Build placeholder list for terminal states
        placeholders = ",".join("?" * len(_TERMINAL_GOAL_STATES))
        with self._conn:
            cursor = self._conn.execute(
                f"""
                UPDATE goal_states
                SET state='interrupted',
                    updated_at=?
                WHERE state NOT IN ({placeholders})
                """,
                (datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 *_TERMINAL_GOAL_STATES),
            )
        return cursor.rowcount

    # ── Legacy JSON Migration ──────────────────────────────────────────

    def _migrate_legacy_json(self) -> None:
        """
        Idempotently import legacy HistoryManager JSON session files.

        Each file in the same directory as the DB (or the sessions directory)
        matching *.json is attempted. Files already migrated (tracked in the
        metadata table) are skipped. Original files are NOT deleted.

        JSON format written by core/chat/history.py:
            {"id": "<session_id>", "messages": [{"role": "user/assistant/system",
             "content": "...", "id": "...", "timestamp": "...", "metadata": {}}]}
        """
        if self._db_path == ":memory:":
            return

        sessions_dir = Path(self._db_path).parent
        json_files = list(sessions_dir.glob("*.json"))
        if not json_files:
            return

        for json_path in json_files:
            flag_key = f"migrated_json_{json_path.stem}"
            already_done = self._conn.execute(
                "SELECT 1 FROM metadata WHERE key=?", (flag_key,)
            ).fetchone()
            if already_done:
                continue

            try:
                self._migrate_one_json(json_path, flag_key)
                logger.info("[SQLiteSessionStore] Migrated legacy JSON: %s", json_path.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[SQLiteSessionStore] Skipped malformed JSON '%s': %s",
                    json_path.name,
                    exc,
                )
                # Mark as attempted so we don't re-try on every startup
                with self._conn:
                    self._conn.execute(
                        """
                        INSERT INTO metadata (key, value) VALUES (?, 'error')
                        ON CONFLICT(key) DO NOTHING
                        """,
                        (flag_key,),
                    )

    def _migrate_one_json(self, json_path: Path, flag_key: str) -> None:
        """Import a single legacy JSON session file."""
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        session_id = data.get("id") or json_path.stem
        raw_messages = data.get("messages", [])

        # Role → sender mapping (HistoryManager uses ChatRole enum values)
        _role_map = {"assistant": "eric", "user": "user", "system": "system", "tool": "system"}

        now = datetime.datetime.now(datetime.timezone.utc)
        title = "Imported Conversation"

        # Derive title from first user message (same logic as SessionManager)
        for m in raw_messages:
            if m.get("role") == "user" and m.get("content"):
                content = m["content"]
                title = content[:30] + ("..." if len(content) > 30 else "")
                break

        session = ChatSession(
            id=session_id,
            title=title,
            is_pinned=False,
            created_at=now,
            updated_at=now,
        )

        with self._conn:
            # Insert session if not already present
            self._conn.execute(
                """
                INSERT OR IGNORE INTO sessions (id, title, is_pinned, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?)
                """,
                (session.id, session.title, now.isoformat(), now.isoformat()),
            )

            for seq, m in enumerate(raw_messages):
                role = m.get("role", "user")
                sender = _role_map.get(role, "user")
                content = m.get("content", "")
                msg_id = m.get("id") or str(seq)
                timestamp_str = m.get("timestamp") or now.isoformat()

                # Skip already-imported messages (INSERT OR IGNORE)
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO messages
                        (id, session_id, sender, content, timestamp, status_indicator, seq)
                    VALUES (?, ?, ?, ?, ?, 'completed', ?)
                    """,
                    (msg_id, session_id, sender, content, timestamp_str, seq),
                )

            # Mark migration done
            self._conn.execute(
                """
                INSERT INTO metadata (key, value) VALUES (?, 'done')
                ON CONFLICT(key) DO UPDATE SET value='done'
                """,
                (flag_key,),
            )

    # ── Internal Helpers ───────────────────────────────────────────────

    def _next_seq(self, session_id: str) -> int:
        """Return the next message sequence number for a session."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) FROM messages WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return (row[0] + 1) if row else 0

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> ChatSession:
        return ChatSession(
            id=row["id"],
            title=row["title"],
            is_pinned=bool(row["is_pinned"]),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ChatMessage:
        return ChatMessage(
            id=row["id"],
            sender=row["sender"],
            content=row["content"],
            timestamp=_parse_dt(row["timestamp"]),
            status_indicator=row["status_indicator"],
        )


def _parse_dt(value: str) -> datetime.datetime:
    """Parse an ISO 8601 datetime string, returning a timezone-aware UTC datetime."""
    dt = datetime.datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt
