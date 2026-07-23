"""
Memory Engine Data Models.

Immutable dataclasses representing memory entries and search results.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.memory.enums import MemorySource, MemoryType, SourceTier


@dataclass(frozen=True)
class MemoryEntry:
    """
    A single unit of memory stored in Eric's memory engine.

    Attributes:
        id: Unique identifier (UUID).
        content: The textual content of the memory.
        memory_type: Classification of the memory (episode, fact, profile).
        source: Origin of the memory (user, agent, consolidation, system).
        timestamp: When the memory was created (UTC).
        metadata: Arbitrary key-value metadata (tags, importance, etc.).
        embedding: Optional vector embedding for semantic search.
    """

    content: str
    memory_type: MemoryType
    source: MemorySource
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Deserialize from a plain dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            source=MemorySource(data["source"]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )


@dataclass(frozen=True)
class SearchResult:
    """
    A ranked result from a memory search operation.

    Attributes:
        entry: The matching MemoryEntry.
        score: Relevance/similarity score (0.0 = no match, 1.0 = exact match).
        source_tier: Which memory tier produced this result.
    """

    entry: MemoryEntry
    score: float
    source_tier: SourceTier
