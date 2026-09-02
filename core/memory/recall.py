"""
Recall Engine — Unified multi-tier memory search.

Searches across short-term, long-term, and vector memory tiers,
merges results, and returns a ranked list.
"""

from core.memory.enums import SourceTier
from core.memory.interfaces import IEmbeddingProvider, IVectorStore
from core.memory.long_term import LongTermMemory
from core.memory.models import MemoryEntry, SearchResult
from core.memory.short_term import ShortTermMemory


class RecallEngine:
    """
    Multi-tier memory recall engine.

    Searches all three tiers (short-term, long-term, vector) and
    returns a merged, deduplicated list of results ranked by score.

    Args:
        short_term: The in-memory conversation buffer.
        long_term: The SQLite-backed persistent store.
        vector_store: The vector similarity search backend.
        embedding_provider: The text-to-vector embedding provider.
    """

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        vector_store: IVectorStore,
        embedding_provider: IEmbeddingProvider,
    ) -> None:
        self._short_term = short_term
        self._long_term = long_term
        self._vector_store = vector_store
        self._embedding = embedding_provider

    def recall(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """
        Search across all memory tiers for the given query.

        Strategy:
        1. Keyword search in short-term memory (high recency weight).
        2. Keyword search in long-term SQLite store.
        3. Vector similarity search via embeddings.
        4. Merge, deduplicate by entry ID, and rank by score.

        Args:
            query: The search query text.
            top_k: Maximum number of results to return.

        Returns:
            Ranked list of SearchResult objects.
        """
        results: dict[str, SearchResult] = {}

        # 1. Short-term keyword search
        st_matches = self._short_term.search(query)
        for entry in st_matches:
            results[entry.id] = SearchResult(
                entry=entry,
                score=0.9,  # High score for recent context
                source_tier=SourceTier.SHORT_TERM,
            )

        # 2. Long-term keyword search
        lt_matches = self._long_term.search_by_keyword(query, limit=top_k)
        for entry in lt_matches:
            if entry.id not in results:
                results[entry.id] = SearchResult(
                    entry=entry,
                    score=0.7,  # Medium score for persistent memory
                    source_tier=SourceTier.LONG_TERM,
                )

        # 3. Vector similarity search
        if self._vector_store.count() > 0:
            query_embedding = self._embedding.embed(query)
            vector_matches = self._vector_store.search(query_embedding, top_k=top_k)
            for entry_id, similarity_score in vector_matches:
                if entry_id not in results:
                    # Try to find the full entry from long-term store
                    lt_entries = self._long_term.search_by_keyword("", limit=1000)
                    entry_map = {e.id: e for e in lt_entries}
                    if entry_id in entry_map:
                        results[entry_id] = SearchResult(
                            entry=entry_map[entry_id],
                            score=similarity_score,
                            source_tier=SourceTier.VECTOR,
                        )

        # Sort by score descending
        ranked = sorted(results.values(), key=lambda r: r.score, reverse=True)
        return ranked[:top_k]
