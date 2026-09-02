"""
In-Memory Vector Store (Development/Testing Adapter).

Pure-Python vector store using cosine similarity.
Designed for dev/test without external dependencies (ChromaDB, FAISS).
Swappable via DI: container.add_singleton(IVectorStore, ChromaVectorStore)
"""

import math
from typing import Any

from core.memory.interfaces import IVectorStore


class InMemoryVectorStore(IVectorStore):
    """
    In-memory vector store using brute-force cosine similarity.

    Suitable for development and testing with small datasets.
    For production, swap to ChromaVectorStore via DI registration.
    """

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def add(self, id: str, embedding: list[float], metadata: dict) -> None:
        """Store a vector with associated metadata."""
        self._vectors[id] = embedding
        self._metadata[id] = metadata

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        """
        Search for the top_k most similar vectors using cosine similarity.

        Returns:
            List of (id, score) tuples sorted by descending similarity.
        """
        if not self._vectors:
            return []

        scores: list[tuple[str, float]] = []
        for id, vector in self._vectors.items():
            score = self._cosine_similarity(query_embedding, vector)
            scores.append((id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def delete(self, id: str) -> None:
        """Delete a vector by its ID."""
        self._vectors.pop(id, None)
        self._metadata.pop(id, None)

    def count(self) -> int:
        """Return the number of stored vectors."""
        return len(self._vectors)

    def get_metadata(self, id: str) -> dict[str, Any] | None:
        """Get metadata for a stored vector."""
        return self._metadata.get(id)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Returns a value in [-1.0, 1.0]. Returns 0.0 if either vector is zero.
        """
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / (norm_a * norm_b)
