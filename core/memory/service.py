"""
Memory Service — Unified facade for all memory operations.

Orchestrates short-term, long-term, and vector memory tiers
behind a single API. Registered as IMemoryService via DI Container.
"""

from dataclasses import replace

from core.config.schemas import SystemConfig
from core.di.interfaces import ILifecycleAware
from core.events import EventBus
from core.logger.interface import ILogger
from core.memory.embedding import DeterministicEmbeddingProvider
from core.memory.enums import MemoryType
from core.memory.interfaces import IEmbeddingProvider, IMemoryService, IVectorStore
from core.memory.long_term import LongTermMemory
from core.memory.models import MemoryEntry, SearchResult
from core.memory.recall import RecallEngine
from core.memory.short_term import ShortTermMemory


class MemoryService(IMemoryService, ILifecycleAware):
    """
    Unified facade orchestrating all memory operations.

    Receives all dependencies via constructor injection (DI).
    Implements ILifecycleAware for managed startup/shutdown.

    Args:
        config: System configuration (for memory settings).
        logger: Logger instance.
        event_bus: Event bus for memory-related events.
        vector_store: Vector database backend.
        embedding: Text embedding provider.
    """

    def __init__(
        self,
        config: SystemConfig,
        logger: ILogger,
        event_bus: EventBus,
        vector_store: IVectorStore,
        embedding: IEmbeddingProvider,
    ) -> None:
        self._config = config
        self._logger = logger
        self._event_bus = event_bus
        self._vector_store = vector_store
        self._embedding = embedding

        # Memory tiers — initialized in initialize()
        mem_cfg = config.memory
        self._short_term = ShortTermMemory(
            max_turns=mem_cfg.short_term.get("max_turns", 20),
        )

        # Determine database path
        db_name = mem_cfg.long_term.get("db_name", "memory.db")
        storage_path = config.app.storage.database_path
        # Use the storage database directory for the memory db
        from pathlib import Path
        db_dir = Path(storage_path).parent
        self._db_path = db_dir / db_name

        self._long_term = LongTermMemory(db_path=self._db_path)
        self._recall_engine: RecallEngine | None = None

    def initialize(self) -> None:
        """Initialize memory tiers and recall engine."""
        self._long_term.initialize()
        self._recall_engine = RecallEngine(
            short_term=self._short_term,
            long_term=self._long_term,
            vector_store=self._vector_store,
            embedding_provider=self._embedding,
        )
        self._logger.info("[MemoryService] Memory Engine initialized.")

    def dispose(self) -> None:
        """Shutdown memory tiers and release resources."""
        self._long_term.dispose()
        self._logger.info("[MemoryService] Memory Engine disposed.")

    # ── IMemoryService Implementation ────────────────────────────────

    def store(self, entry: MemoryEntry) -> None:
        """
        Store a memory entry across appropriate tiers.

        - All entries go to short-term buffer.
        - FACT and PROFILE entries are persisted to long-term.
        - Entries with embeddings are indexed in the vector store.
        """
        # 1. Short-term (always)
        self._short_term.add(entry)

        # 2. Generate embedding if not present
        if entry.embedding is None:
            embedding = self._embedding.embed(entry.content)
            entry = replace(entry, embedding=embedding)

        # 3. Long-term (for facts and profile)
        if entry.memory_type in (MemoryType.FACT, MemoryType.PROFILE):
            self._long_term.store(entry)

        # 4. Vector store (if embedding available)
        if entry.embedding:
            self._vector_store.add(
                id=entry.id,
                embedding=entry.embedding,
                metadata={"memory_type": entry.memory_type.value, "source": entry.source.value},
            )

        self._logger.debug(f"[MemoryService] Stored: {entry.memory_type.value} ({entry.id[:8]}...)")

    def recall(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search across all memory tiers and return ranked results."""
        if self._recall_engine is None:
            return []
        results = self._recall_engine.recall(query, top_k=top_k)
        self._logger.debug(f"[MemoryService] Recall '{query[:30]}...' → {len(results)} results")
        return results

    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """Get the N most recent entries from short-term memory."""
        return self._short_term.get_recent(n)

    def clear_short_term(self) -> None:
        """Clear all entries from short-term memory buffer."""
        count = self._short_term.count()
        self._short_term.clear()
        self._logger.info(f"[MemoryService] Short-term cleared ({count} entries)")
