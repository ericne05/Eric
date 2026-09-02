"""
Short-Term Memory (In-Memory Conversation Buffer).

Stores the most recent conversation turns and actions in RAM.
Configurable via MemoryConfig.short_term.max_turns.
"""

from core.memory.models import MemoryEntry


class ShortTermMemory:
    """
    In-memory circular buffer for recent conversation context.

    When the buffer exceeds max_turns, the oldest entries are discarded.
    Future: emit 'memory.short_term.overflow' event for consolidation.

    Args:
        max_turns: Maximum number of entries to retain.
    """

    def __init__(self, max_turns: int = 20) -> None:
        self._max_turns = max_turns
        self._entries: list[MemoryEntry] = []

    @property
    def max_turns(self) -> int:
        """Maximum buffer capacity."""
        return self._max_turns

    def add(self, entry: MemoryEntry) -> MemoryEntry | None:
        """
        Add an entry to the buffer.

        Returns:
            The evicted entry if the buffer was full, otherwise None.
        """
        evicted: MemoryEntry | None = None
        if len(self._entries) >= self._max_turns:
            evicted = self._entries.pop(0)
        self._entries.append(entry)
        return evicted

    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """Get the N most recent entries (newest last)."""
        return list(self._entries[-n:])

    def get_all(self) -> list[MemoryEntry]:
        """Get all entries in chronological order."""
        return list(self._entries)

    def clear(self) -> list[MemoryEntry]:
        """Clear the buffer and return all evicted entries."""
        entries = list(self._entries)
        self._entries.clear()
        return entries

    def count(self) -> int:
        """Number of entries currently in the buffer."""
        return len(self._entries)

    def search(self, keyword: str) -> list[MemoryEntry]:
        """Simple keyword search across entry content."""
        keyword_lower = keyword.lower()
        return [e for e in self._entries if keyword_lower in e.content.lower()]
