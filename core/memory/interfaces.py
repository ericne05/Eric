"""
Memory Engine Interfaces.

Abstract contracts for the Memory subsystem. All implementations
are registered via DI Container and swappable without code changes.
"""

from abc import ABC, abstractmethod

from core.memory.enums import MemoryType
from core.memory.models import MemoryEntry, SearchResult


class IEmbeddingProvider(ABC):
    """
    Contract for text embedding backends.

    Implementations: DeterministicEmbeddingProvider (dev/test),
    GeminiEmbeddingProvider, OpenAIEmbeddingProvider (future).
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""

    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""


class IVectorStore(ABC):
    """
    Contract for vector database backends.

    Implementations: InMemoryVectorStore (dev/test),
    ChromaVectorStore, FAISSVectorStore (future).
    """

    @abstractmethod
    def add(self, id: str, embedding: list[float], metadata: dict) -> None:
        """Store a vector with associated metadata."""

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        """Search for the top_k most similar vectors. Returns list of (id, score)."""

    @abstractmethod
    def delete(self, id: str) -> None:
        """Delete a vector by its ID."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored vectors."""


class IMemoryService(ABC):
    """
    Facade contract for the unified Memory Engine.

    Orchestrates short-term, long-term, and vector memory tiers
    behind a single API.
    """

    @abstractmethod
    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry across appropriate tiers."""

    @abstractmethod
    def recall(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search across all memory tiers and return ranked results."""

    @abstractmethod
    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """Get the N most recent entries from short-term memory."""

    @abstractmethod
    def clear_short_term(self) -> None:
        """Clear all entries from short-term memory buffer."""
