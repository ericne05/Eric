"""
Long-Term Memory (SQLite-based Persistent Storage).

Stores episodes, facts, and user profile data in a local SQLite database.
Implements ILifecycleAware for managed connection lifecycle.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from core.di.interfaces import ILifecycleAware
from core.memory.enums import MemorySource, MemoryType
from core.memory.models import MemoryEntry


class LongTermMemory(ILifecycleAware):
    """
    SQLite-backed persistent memory store for episodes, facts, and profile.

    Lifecycle:
        initialize() → creates tables if they don't exist.
        dispose()     → closes the SQLite connection.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Create database directory and tables."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def dispose(self) -> None:
        """Close the SQLite connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self) -> None:
        """Create the memory tables if they don't exist."""
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding TEXT DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp);
        """)
        self._conn.commit()

    def store(self, entry: MemoryEntry) -> None:
        """Insert a memory entry into the database."""
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT OR REPLACE INTO memories (id, content, memory_type, source, timestamp, metadata, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.content,
                entry.memory_type.value,
                entry.source.value,
                entry.timestamp.isoformat(),
                json.dumps(entry.metadata),
                json.dumps(entry.embedding) if entry.embedding else None,
            ),
        )
        self._conn.commit()

    def search_by_keyword(self, keyword: str, limit: int = 10) -> list[MemoryEntry]:
        """Search memories by keyword in content."""
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_by_type(self, memory_type: MemoryType, limit: int = 10) -> list[MemoryEntry]:
        """Get memories filtered by type."""
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE memory_type = ? ORDER BY timestamp DESC LIMIT ?",
            (memory_type.value, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get the most recent memories across all types."""
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def count(self) -> int:
        """Total number of stored memories."""
        assert self._conn is not None
        row = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0]

    def delete(self, id: str) -> None:
        """Delete a memory by ID."""
        assert self._conn is not None
        self._conn.execute("DELETE FROM memories WHERE id = ?", (id,))
        self._conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """Convert a database row to a MemoryEntry."""
        from datetime import datetime

        embedding_raw = row["embedding"]
        embedding = json.loads(embedding_raw) if embedding_raw else None

        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            source=MemorySource(row["source"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata"]),
            embedding=embedding,
        )
