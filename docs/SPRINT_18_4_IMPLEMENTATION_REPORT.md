# Sprint 18.4 Implementation Report — Session Persistence & State Restoration

## Summary

Sprint 18.4 introduces durable SQLite-based session persistence for the Eric Windows Desktop Assistant. Chat sessions, messages, pinned state, and minimal goal summaries now survive application restarts. Legacy JSON session files written by the deprecated `HistoryManager` are migrated idempotently on first startup.

---

## Architecture

```
app/persistence/
├── __init__.py         — Package exports
├── interfaces.py       — ISessionRepository (ABC)
├── session_store.py    — SQLiteSessionStore (ILifecycleAware + ISessionRepository)
└── module.py           — SessionPersistenceModule (DI registration)

app/services/session_manager.py   — Modified: optional ISessionRepository injection
core/kernel/kernel.py             — Modified: SessionPersistenceModule registered in DI
```

### Dependency Direction

```
app/persistence → app/services (ChatSession, ChatMessage models)
app/persistence → core/di (ILifecycleAware)
app/persistence → core/utils (get_app_data_dir)

app/persistence does NOT depend on:
  - core/runtime (no RuntimeHost, EventBus, GoalManager)
  - app/client (no EricClient)
  - app/lifecycle (no CompanionApplication)
  - UI/presentation layer
```

---

## SQLite Schema

Database file: `%LOCALAPPDATA%\Eric\sessions\sessions.db`

```sql
-- Chat sessions
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT 'New Conversation',
    is_pinned   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Chat messages (insertion-order via seq column)
CREATE TABLE IF NOT EXISTS messages (
    id               TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL,
    sender           TEXT NOT NULL,           -- 'user', 'eric', 'system'
    content          TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    status_indicator TEXT NOT NULL DEFAULT 'completed',
    seq              INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, seq);

-- Goal state summaries (transport-safe only — no live objects)
CREATE TABLE IF NOT EXISTS goal_states (
    goal_id     TEXT PRIMARY KEY,
    session_id  TEXT,
    title       TEXT NOT NULL DEFAULT '',
    intent      TEXT NOT NULL DEFAULT '',
    state       TEXT NOT NULL,
    result_json TEXT,                         -- NULL or JSON string
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goal_states_session ON goal_states(session_id);

-- Key/value metadata (last_session_id, migration flags)
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**PRAGMAs applied:** `journal_mode=WAL`, `foreign_keys=ON`

---

## Legacy JSON Migration

| Behaviour | Detail |
|-----------|--------|
| Source files | `%LOCALAPPDATA%\Eric\sessions\*.json` (written by old `HistoryManager`) |
| Format | `{"id": "...", "messages": [{"role": "user/assistant/system", "content": "..."}]}` |
| Role mapping | `assistant` → `sender="eric"`, `user` → `"user"`, `system` → `"system"` |
| Idempotency | Migration flag `migrated_json_<stem>=done` stored in `metadata` table |
| Malformed files | Caught per-file; error flag written; other files still migrated |
| Original files | **NOT deleted or modified** |
| Trigger | Called once during `SQLiteSessionStore.initialize()` |

---

## Session Restore Behaviour

1. On `SessionManager.__init__(repository=store)`: calls `_load_from_repo()` which hydrates the in-memory `_sessions` dict from all persisted sessions + their messages.
2. `_active_session_id` is set from `repository.get_last_session_id()`.
3. On `restore_last_session()`: the repository's `last_session_id` is checked first; falls back to most-recently-updated in-memory session if unset.
4. `set_last_session_id()` is called on every `create_session()` call.

---

## Minimal Goal State Behaviour

Only transport-safe fields are stored:

| Field | Type | Notes |
|-------|------|-------|
| `goal_id` | TEXT | UUID |
| `session_id` | TEXT | nullable |
| `title` | TEXT | from GoalSpecification |
| `intent` | TEXT | from GoalSpecification |
| `state` | TEXT | GoalState enum value string |
| `result_json` | TEXT | nullable JSON string (`GoalResult` summary) |
| `created_at`, `updated_at` | TEXT | ISO 8601 UTC |

**Never stored**: ExecutionPlan, SubGoals, DAGRelation, GoalProgress.current_runtime, adapters, coroutines, callbacks, EventBus refs.

**Interrupted goal normalization**: On every `initialize()`, goals with non-terminal state (`running`, `planning`, `estimating`, `ready`, `waiting`, `recovering`, `paused`) are set to `state='interrupted'`. Terminal states (`completed`, `failed`, `cancelled`, `interrupted`) are never changed. Eric does NOT auto-resume goals on startup.

---

## Files Created / Modified

| Action | File |
|--------|------|
| CREATED | `app/persistence/__init__.py` |
| CREATED | `app/persistence/interfaces.py` |
| CREATED | `app/persistence/session_store.py` |
| CREATED | `app/persistence/module.py` |
| MODIFIED | `app/services/session_manager.py` |
| MODIFIED | `core/kernel/kernel.py` |
| CREATED | `tests/unit/test_sprint18_4_session_persistence.py` |
| CREATED | `docs/SPRINT_18_4_IMPLEMENTATION_REPORT.md` |
| MODIFIED | `PROJECT_STATUS.md` |

---

## Test Results

**Targeted (Sprint 18.4 only):** 31 passed, 0 failed

| Test Class | Tests | Result |
|------------|-------|--------|
| `TestRepositoryCRUD` | 5 | ✅ |
| `TestMessagePersistence` | 3 | ✅ |
| `TestMetadataSurvival` | 2 | ✅ |
| `TestRestoreLastSession` | 3 | ✅ |
| `TestLegacyJsonMigration` | 5 | ✅ |
| `TestGoalStatePersistence` | 5 | ✅ |
| `TestSessionManagerIntegration` | 5 | ✅ |
| `TestStorageIsolation` | 3 | ✅ |

**Full suite:** 371 passed, 2 failed (same 2 pre-existing Playwright failures as baseline)

---

## Sprint 17.5 Hardening Rules — Regression Check

| Rule | Status |
|------|--------|
| `.env` not bundled | ✅ Not touched |
| `BackendBridge` no `shell=True` | ✅ Not touched |
| Single composition root (`AppBootstrap` + Kernel DI) | ✅ `SessionPersistenceModule` registered in Kernel DI |
| `WindowsDesktopAdapter.execute()` propagates failures | ✅ Not touched |
| `GoalSpecification.parameters` survives pipeline | ✅ Not touched |
| `LLMRouter` is single routing authority | ✅ Not touched |
| `LLMService` is only a facade | ✅ Not touched |
| Production model never defaults to `dummy-v1` | ✅ Not touched |

---

## Commit

`feat(session): add durable SQLite session persistence`
