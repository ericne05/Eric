"""
Memory Module Registration for DI Container.

Registers all memory subsystem services into the DI Container.
Each interface maps to its development/testing implementation,
swappable for production implementations (ChromaDB, Gemini, etc.).
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class MemoryModule(IDependencyModule):
    """
    Registers the Memory Engine services into the DI Container.

    Default registrations (dev/test):
        IEmbeddingProvider → DeterministicEmbeddingProvider
        IVectorStore       → InMemoryVectorStore
        IMemoryService     → MemoryService

    To swap for production::

        container.add_singleton(IEmbeddingProvider, GeminiEmbeddingProvider)
        container.add_singleton(IVectorStore, ChromaVectorStore)
    """

    def register(self, container: "Container") -> None:
        from core.memory.embedding import DeterministicEmbeddingProvider
        from core.memory.interfaces import (
            IEmbeddingProvider,
            IMemoryService,
            IVectorStore,
        )
        from core.memory.service import MemoryService
        from core.memory.vector_store import InMemoryVectorStore

        container.add_singleton(IEmbeddingProvider, DeterministicEmbeddingProvider)
        container.add_singleton(IVectorStore, InMemoryVectorStore)
        container.add_singleton(IMemoryService, MemoryService)
