"""
tests/unit/test_sprint18_4_session_persistence.py

Sprint 18.4 — Session Persistence & State Restoration Tests.

All tests use tmp_path (pytest fixture) for complete isolation.
The real %LOCALAPPDATA%\\Eric directory is NEVER touched.

Coverage:
    - Repository CRUD (create, list, update, delete, messages)
    - Session title and pinned status survive restart
    - Messages survive restart in insertion order
    - Restore last session from persisted last_session_id
    - Deleted session stays deleted after restart
    - Legacy JSON migration (idempotent, no duplicates, no crash on malformed)
    - Goal state persistence (transport-safe fields only)
    - Interrupted goal normalization on startup
    - SessionManager backward compatibility without repository
    - SessionManager integration with repository
    - Isolation: never touches real %LOCALAPPDATA%\\Eric
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from pathlib import Path
from typing import Optional

import pytest

from app.persistence.interfaces import ISessionRepository
from app.persistence.session_store import SQLiteSessionStore
from app.services.session_manager import ChatMessage, ChatSession, SessionManager


# ── Fixtures ──────────────────────────────────────────────────────────────────


def make_store(path: str) -> SQLiteSessionStore:
    """Create and initialize a SQLiteSessionStore at the given path."""
    store = SQLiteSessionStore(path)
    store.initialize()
    return store


def reopen_store(path: str) -> SQLiteSessionStore:
    """Simulate restart: create a fresh store at the same path (no initialize called yet by caller)."""
    store = SQLiteSessionStore(path)
    store.initialize()
    return store


def make_session(title: str = "Test Session", is_pinned: bool = False) -> ChatSession:
    now = datetime.datetime.now(datetime.timezone.utc)
    return ChatSession(
        id=str(uuid.uuid4()),
        title=title,
        is_pinned=is_pinned,
        created_at=now,
        updated_at=now,
    )


def make_message(content: str, sender: str = "user", status: str = "completed") -> ChatMessage:
    return ChatMessage(
        id=str(uuid.uuid4()),
        sender=sender,
        content=content,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        status_indicator=status,
    )


# ── 1. Repository CRUD: create → persist → reopen → load ─────────────────────


class TestRepositoryCRUD:
    def test_create_persist_reopen_load(self, tmp_path):
        """Session created in store A survives a restart (store B)."""
        db = str(tmp_path / "sessions.db")
        store_a = make_store(db)
        session = make_session("My Session")
        store_a.create_session(session)
        store_a.dispose()

        store_b = reopen_store(db)
        loaded = store_b.get_session(session.id)
        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.title == "My Session"
        assert loaded.is_pinned is False
        store_b.dispose()

    def test_list_sessions_returns_all(self, tmp_path):
        """list_sessions() returns all persisted sessions."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        ids = set()
        for i in range(3):
            s = make_session(f"Session {i}")
            store.create_session(s)
            ids.add(s.id)
        store.dispose()

        store2 = reopen_store(db)
        sessions = store2.list_sessions()
        assert len(sessions) == 3
        assert {s.id for s in sessions} == ids
        store2.dispose()

    def test_update_session_metadata(self, tmp_path):
        """update_session() persists title, is_pinned, and updated_at changes."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session("Original Title")
        store.create_session(session)

        session.title = "Renamed Title"
        session.is_pinned = True
        session.updated_at = datetime.datetime.now(datetime.timezone.utc)
        store.update_session(session)
        store.dispose()

        store2 = reopen_store(db)
        loaded = store2.get_session(session.id)
        assert loaded.title == "Renamed Title"
        assert loaded.is_pinned is True
        store2.dispose()

    def test_delete_session(self, tmp_path):
        """delete_session() removes the session from persistent storage."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session("To Be Deleted")
        store.create_session(session)
        store.delete_session(session.id)
        store.dispose()

        store2 = reopen_store(db)
        loaded = store2.get_session(session.id)
        assert loaded is None
        store2.dispose()

    def test_delete_session_stays_deleted_after_restart(self, tmp_path):
        """Deleted session is not re-hydrated by list_sessions on next startup."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        s1 = make_session("Keep Me")
        s2 = make_session("Delete Me")
        store.create_session(s1)
        store.create_session(s2)
        store.delete_session(s2.id)
        store.dispose()

        store2 = reopen_store(db)
        ids = {s.id for s in store2.list_sessions()}
        assert s1.id in ids
        assert s2.id not in ids
        store2.dispose()


# ── 2. Messages: survive restart in order ─────────────────────────────────────


class TestMessagePersistence:
    def test_messages_survive_restart_in_order(self, tmp_path):
        """5 messages written in order are loaded in the same order after restart."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)

        expected_contents = [f"Message {i}" for i in range(5)]
        for content in expected_contents:
            msg = make_message(content, sender="user" if int(content[-1]) % 2 == 0 else "eric")
            store.add_message(session.id, msg)
        store.dispose()

        store2 = reopen_store(db)
        messages = store2.get_messages(session.id)
        assert len(messages) == 5
        assert [m.content for m in messages] == expected_contents
        store2.dispose()

    def test_message_fields_preserved(self, tmp_path):
        """All ChatMessage fields are preserved exactly."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)

        ts = datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        msg = ChatMessage(
            id="fixed-id-abc",
            sender="eric",
            content="Hello from Eric",
            timestamp=ts,
            status_indicator="completed",
        )
        store.add_message(session.id, msg)
        store.dispose()

        store2 = reopen_store(db)
        messages = store2.get_messages(session.id)
        assert len(messages) == 1
        m = messages[0]
        assert m.id == "fixed-id-abc"
        assert m.sender == "eric"
        assert m.content == "Hello from Eric"
        assert m.status_indicator == "completed"
        assert m.timestamp == ts
        store2.dispose()

    def test_messages_deleted_with_session_cascade(self, tmp_path):
        """Deleting a session also deletes all its messages (ON DELETE CASCADE)."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)
        for i in range(3):
            store.add_message(session.id, make_message(f"msg {i}"))
        store.delete_session(session.id)
        store.dispose()

        store2 = reopen_store(db)
        messages = store2.get_messages(session.id)
        assert messages == []
        store2.dispose()


# ── 3. Metadata: title and pinned status survive restart ──────────────────────


class TestMetadataSurvival:
    def test_title_and_pinned_survive_restart(self, tmp_path):
        """Session title and is_pinned flag are correctly reloaded after restart."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session("My Important Chat", is_pinned=True)
        store.create_session(session)
        store.dispose()

        store2 = reopen_store(db)
        loaded = store2.get_session(session.id)
        assert loaded.title == "My Important Chat"
        assert loaded.is_pinned is True
        store2.dispose()

    def test_list_sessions_ordering_pinned_first(self, tmp_path):
        """list_sessions() returns pinned sessions before unpinned, then by updated_at desc."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)

        t_old = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        t_new = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)

        pinned = ChatSession(id=str(uuid.uuid4()), title="Pinned", is_pinned=True,
                             created_at=t_old, updated_at=t_old)
        normal = ChatSession(id=str(uuid.uuid4()), title="Normal (newer)", is_pinned=False,
                             created_at=t_new, updated_at=t_new)

        store.create_session(normal)
        store.create_session(pinned)
        store.dispose()

        store2 = reopen_store(db)
        sessions = store2.list_sessions()
        assert sessions[0].id == pinned.id, "Pinned session must be first"
        store2.dispose()


# ── 4. Restore last session ────────────────────────────────────────────────────


class TestRestoreLastSession:
    def test_restore_returns_correct_last_session(self, tmp_path):
        """get_last_session_id() returns the ID set by set_last_session_id()."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        s1 = make_session("First")
        s2 = make_session("Second")
        s3 = make_session("Third")
        store.create_session(s1)
        store.create_session(s2)
        store.create_session(s3)
        store.set_last_session_id(s2.id)
        store.dispose()

        store2 = reopen_store(db)
        last_id = store2.get_last_session_id()
        assert last_id == s2.id
        store2.dispose()

    def test_get_last_session_id_none_when_unset(self, tmp_path):
        """get_last_session_id() returns None when no session has been set."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        assert store.get_last_session_id() is None
        store.dispose()

    def test_session_manager_restore_last_session(self, tmp_path):
        """SessionManager.restore_last_session() returns the persisted last session."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)

        mgr = SessionManager(repository=store)
        s1 = mgr.create_session("Alpha")
        s2 = mgr.create_session("Beta")  # Active after creation
        mgr.restore_last_session()  # Should return Beta (most recent)
        store.dispose()

        # Simulate restart
        store2 = reopen_store(db)
        mgr2 = SessionManager(repository=store2)
        restored = mgr2.restore_last_session()
        assert restored is not None
        assert restored.id == s2.id
        store2.dispose()


# ── 5. Legacy JSON migration ───────────────────────────────────────────────────


class TestLegacyJsonMigration:
    def _write_legacy_json(self, sessions_dir: Path, session_id: str, messages: list) -> None:
        """Write a HistoryManager-format JSON file."""
        data = {
            "id": session_id,
            "messages": messages,
            "message_count": len(messages),
            "turn_count": sum(1 for m in messages if m.get("role") == "user"),
        }
        (sessions_dir / f"{session_id}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def test_legacy_json_migration_imports_messages(self, tmp_path):
        """Legacy JSON file is imported on first initialize()."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_id = str(uuid.uuid4())
        self._write_legacy_json(
            sessions_dir,
            session_id,
            [
                {"id": "m1", "role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00"},
                {"id": "m2", "role": "assistant", "content": "Hi there", "timestamp": "2026-01-01T10:01:00"},
            ],
        )

        db = str(sessions_dir / "sessions.db")
        store = make_store(db)
        msgs = store.get_messages(session_id)
        assert len(msgs) == 2
        assert msgs[0].sender == "user"
        assert msgs[0].content == "Hello"
        assert msgs[1].sender == "eric"  # assistant → eric
        assert msgs[1].content == "Hi there"
        store.dispose()

    def test_legacy_json_migration_is_idempotent(self, tmp_path):
        """Running migration twice does not duplicate messages."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_id = str(uuid.uuid4())
        self._write_legacy_json(
            sessions_dir,
            session_id,
            [
                {"id": "m1", "role": "user", "content": "Only once"},
            ],
        )

        db = str(sessions_dir / "sessions.db")
        store = make_store(db)
        store.dispose()

        # Second initialize — must not duplicate
        store2 = reopen_store(db)
        msgs = store2.get_messages(session_id)
        assert len(msgs) == 1, f"Expected 1 message, got {len(msgs)}"
        store2.dispose()

    def test_malformed_json_does_not_crash(self, tmp_path):
        """A malformed JSON file causes a warning but no crash, and other files are still processed."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # Write a valid session
        good_id = str(uuid.uuid4())
        self._write_legacy_json(
            sessions_dir, good_id,
            [{"id": "x1", "role": "user", "content": "Valid msg"}],
        )

        # Write a malformed JSON
        (sessions_dir / "bad_session.json").write_text("{not valid json!!!", encoding="utf-8")

        db = str(sessions_dir / "sessions.db")
        # Must not raise
        store = make_store(db)
        # Good session was imported
        msgs = store.get_messages(good_id)
        assert len(msgs) == 1
        store.dispose()

    def test_original_json_files_not_deleted(self, tmp_path):
        """Migration does NOT delete or modify the original JSON files."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_id = str(uuid.uuid4())
        json_path = sessions_dir / f"{session_id}.json"
        self._write_legacy_json(
            sessions_dir, session_id,
            [{"id": "m1", "role": "user", "content": "Keep original"}],
        )
        original_content = json_path.read_text(encoding="utf-8")

        db = str(sessions_dir / "sessions.db")
        store = make_store(db)
        store.dispose()

        assert json_path.exists(), "Original JSON file must not be deleted"
        assert json_path.read_text(encoding="utf-8") == original_content, "Original JSON must not be modified"

    def test_migration_handles_empty_messages_array(self, tmp_path):
        """A JSON file with an empty messages array is imported without error."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_id = str(uuid.uuid4())
        self._write_legacy_json(sessions_dir, session_id, [])

        db = str(sessions_dir / "sessions.db")
        store = make_store(db)
        # Session exists (imported), messages are empty
        msgs = store.get_messages(session_id)
        assert msgs == []
        store.dispose()


# ── 6. Goal state persistence ─────────────────────────────────────────────────


class TestGoalStatePersistence:
    def test_goal_state_survives_restart(self, tmp_path):
        """Transport-safe goal state fields are correctly reloaded after restart."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)

        goal_id = str(uuid.uuid4())
        store.save_goal_state(
            goal_id=goal_id,
            session_id=session.id,
            title="Open Notepad",
            intent="launch_application",
            state="completed",
            result_json='{"success": true, "output_data": {"app": "notepad"}}',
        )
        store.dispose()

        store2 = reopen_store(db)
        goals = store2.load_goal_states(session.id)
        assert len(goals) == 1
        g = goals[0]
        assert g["goal_id"] == goal_id
        assert g["title"] == "Open Notepad"
        assert g["intent"] == "launch_application"
        assert g["state"] == "completed"
        assert g["result_json"] is not None
        store2.dispose()

    def test_goal_state_upsert(self, tmp_path):
        """save_goal_state() with the same goal_id updates the existing record."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)
        goal_id = str(uuid.uuid4())

        store.save_goal_state(goal_id, session.id, "Task", "do_thing", "running", None)
        store.save_goal_state(goal_id, session.id, "Task", "do_thing", "completed", '{"success":true}')

        goals = store.load_goal_states(session.id)
        assert len(goals) == 1
        assert goals[0]["state"] == "completed"
        store.dispose()

    def test_interrupted_goal_normalized_on_startup(self, tmp_path):
        """Goals stored with active state are normalized to 'interrupted' on next startup."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)

        # Save a goal that was RUNNING at time of previous shutdown
        goal_id = str(uuid.uuid4())
        store.save_goal_state(goal_id, session.id, "Running Task", "do_stuff", "running", None)
        store.dispose()

        # Simulate restart — normalize_interrupted_goals() is called in initialize()
        store2 = reopen_store(db)
        goals = store2.load_goal_states(session.id)
        assert len(goals) == 1
        assert goals[0]["state"] == "interrupted", (
            f"Expected 'interrupted', got '{goals[0]['state']}'"
        )
        store2.dispose()

    def test_terminal_goals_not_modified_on_startup(self, tmp_path):
        """Terminal goal states (completed, failed, cancelled, interrupted) are never re-normalized."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)

        terminal_states = ["completed", "failed", "cancelled", "interrupted"]
        for state in terminal_states:
            gid = str(uuid.uuid4())
            store.save_goal_state(gid, session.id, f"Task {state}", "intent", state, None)
        store.dispose()

        store2 = reopen_store(db)
        goals = store2.load_goal_states(session.id)
        assert len(goals) == len(terminal_states)
        actual_states = {g["state"] for g in goals}
        assert actual_states == set(terminal_states), (
            f"Terminal states were modified: {actual_states}"
        )
        store2.dispose()

    def test_no_live_objects_in_goal_state(self, tmp_path):
        """Confirm that goal_state only stores primitive/JSON-safe fields — no live object refs."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        session = make_session()
        store.create_session(session)

        # result_json must be a plain string (JSON serialized) or None
        result_json = json.dumps({"success": True, "output_data": {"app": "notepad"}})
        goal_id = str(uuid.uuid4())
        store.save_goal_state(goal_id, session.id, "T", "i", "completed", result_json)

        goals = store.load_goal_states(session.id)
        g = goals[0]

        # All values must be primitive (str, None) — no live objects
        for key, value in g.items():
            assert not callable(value), f"Field '{key}' contains a callable"
            assert not hasattr(value, "__aiter__"), f"Field '{key}' contains a coroutine"
        store.dispose()


# ── 7. SessionManager integration ────────────────────────────────────────────


class TestSessionManagerIntegration:
    def test_session_manager_pure_memory_without_repo(self):
        """SessionManager(repository=None) works identically to the original in-memory mode."""
        mgr = SessionManager()  # No repository
        session = mgr.create_session("Test")
        msg = mgr.add_message("Hello", sender="user")
        assert msg.content == "Hello"
        assert len(mgr.get_active_session().messages) == 1
        assert mgr.pin_session(session.id, True) is True
        assert mgr.get_active_session().is_pinned is True

    def test_session_manager_persists_via_repository(self, tmp_path):
        """SessionManager writes through to repository on every mutation."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        mgr = SessionManager(repository=store)

        session = mgr.create_session("Persisted")
        mgr.add_message("first message", sender="user")
        mgr.add_message("reply", sender="eric")
        mgr.pin_session(session.id, True)
        store.dispose()

        # Restart: fresh store + fresh SessionManager
        store2 = reopen_store(db)
        mgr2 = SessionManager(repository=store2)

        sessions = mgr2.list_sessions()
        assert len(sessions) == 1
        s = sessions[0]
        assert s.title == "first message..."[:30] or s.title.startswith("first")
        assert s.is_pinned is True
        assert len(s.messages) == 2
        assert s.messages[0].content == "first message"
        assert s.messages[1].content == "reply"
        store2.dispose()

    def test_session_manager_delete_removes_from_repo(self, tmp_path):
        """SessionManager.delete_session() removes from both memory and repository."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        mgr = SessionManager(repository=store)

        s = mgr.create_session("Temporary")
        mgr.add_message("msg", sender="user")
        assert mgr.delete_session(s.id) is True
        store.dispose()

        store2 = reopen_store(db)
        mgr2 = SessionManager(repository=store2)
        assert mgr2.get_session(s.id) is None
        assert len(mgr2.list_sessions()) == 0
        store2.dispose()

    def test_session_manager_restores_last_session_on_startup(self, tmp_path):
        """SessionManager repopulates _active_session_id from the repository on startup."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        mgr = SessionManager(repository=store)

        _s1 = mgr.create_session("One")
        s2 = mgr.create_session("Two")
        # s2 is the last created; set_last_session_id was called on creation
        store.dispose()

        store2 = reopen_store(db)
        mgr2 = SessionManager(repository=store2)
        restored = mgr2.restore_last_session()
        assert restored is not None
        assert restored.id == s2.id
        store2.dispose()

    def test_session_manager_multiple_sessions_survive_restart(self, tmp_path):
        """Multiple sessions with different titles all survive a restart."""
        db = str(tmp_path / "sessions.db")
        store = make_store(db)
        mgr = SessionManager(repository=store)

        titles = ["Alpha", "Beta", "Gamma"]
        created_ids = set()
        for title in titles:
            s = mgr.create_session(title)
            created_ids.add(s.id)
        store.dispose()

        store2 = reopen_store(db)
        mgr2 = SessionManager(repository=store2)
        sessions = mgr2.list_sessions()
        assert len(sessions) == 3
        loaded_ids = {s.id for s in sessions}
        assert loaded_ids == created_ids
        store2.dispose()


# ── 8. Isolation: never touch real %LOCALAPPDATA%\\Eric ───────────────────────


class TestStorageIsolation:
    def test_tmp_path_db_never_in_eric_data_dir(self, tmp_path):
        """All test operations use tmp_path; the real Eric data directory is never accessed."""
        real_localappdata = os.environ.get("LOCALAPPDATA", "")
        eric_data_dir = os.path.join(real_localappdata, "Eric") if real_localappdata else ""
        db_path = str(tmp_path / "isolated_sessions.db")

        # tmp_path must NOT be inside the real Eric data directory.
        # (tmp_path on Windows may share the AppData\\Local prefix with LOCALAPPDATA,
        # which is fine — what matters is it is NOT under AppData\\Local\\Eric.)
        if eric_data_dir:
            assert not db_path.startswith(eric_data_dir), (
                f"Test DB path must not be inside the Eric data dir '{eric_data_dir}'"
            )

        store = make_store(db_path)
        session = make_session("Isolation Test")
        store.create_session(session)
        store.dispose()

        # Verify the DB was created at the expected tmp location
        assert Path(db_path).exists()

        # The real Eric sessions.db must be a different path from our test DB
        real_sessions_db = (
            os.path.join(eric_data_dir, "sessions", "sessions.db") if eric_data_dir else ""
        )
        assert db_path != real_sessions_db

    def test_memory_db_leaves_no_files(self, tmp_path):
        """Using ':memory:' leaves no files on disk at all."""
        store = SQLiteSessionStore(":memory:")
        store.initialize()
        session = make_session("Memory Test")
        store.create_session(session)
        msg = make_message("hello")
        store.add_message(session.id, msg)

        # Everything in memory
        sessions = store.list_sessions()
        assert len(sessions) == 1
        msgs = store.get_messages(session.id)
        assert len(msgs) == 1

        store.dispose()
        # No DB file created
        assert not any(f.suffix == ".db" for f in tmp_path.iterdir() if tmp_path.exists())

    def test_irepository_is_abstract(self):
        """ISessionRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ISessionRepository()  # type: ignore[abstract]
