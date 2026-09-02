"""
Eric Memory Engine Module.

Provides the Memory subsystem with multi-tier storage (short-term, long-term, vector),
embedding interfaces, and a unified MemoryService facade.

Public API::

    from core.memory import IMemoryService, IVectorStore, IEmbeddingProvider
    from core.memory import MemoryEntry, SearchResult
    from core.memory import MemoryType, MemorySource, SourceTier
"""

from core.memory.embedding import DeterministicEmbeddingProvider
from core.memory.enums import MemorySource, MemoryType, SourceTier
from core.memory.interfaces import IEmbeddingProvider, IMemoryService, IVectorStore
from core.memory.long_term import LongTermMemory
from core.memory.models import MemoryEntry, SearchResult
from core.memory.recall import RecallEngine
from core.memory.service import MemoryService
from core.memory.short_term import ShortTermMemory
from core.memory.vector_store import InMemoryVectorStore

__all__ = [
    # Enums
    "MemoryType",
    "MemorySource",
    "SourceTier",
    # Models
    "MemoryEntry",
    "SearchResult",
    # Interfaces
    "IMemoryService",
    "IVectorStore",
    "IEmbeddingProvider",
    # Implementations
    "MemoryService",
    "ShortTermMemory",
    "LongTermMemory",
    "InMemoryVectorStore",
    "DeterministicEmbeddingProvider",
    "RecallEngine",
]
