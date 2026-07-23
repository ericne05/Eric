"""
Unit tests for the Memory Engine (Sprint 6).
"""

import pytest

from core.memory.embedding import DeterministicEmbeddingProvider
from core.memory.enums import MemorySource, MemoryType, SourceTier
from core.memory.interfaces import IEmbeddingProvider, IMemoryService, IVectorStore
from core.memory.long_term import LongTermMemory
from core.memory.models import MemoryEntry, SearchResult
from core.memory.recall import RecallEngine
from core.memory.service import MemoryService
from core.memory.short_term import ShortTermMemory
from core.memory.vector_store import InMemoryVectorStore


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_entry(
    content: str = "test memory",
    memory_type: MemoryType = MemoryType.EPISODE,
    source: MemorySource = MemorySource.USER,
    **kwargs,
) -> MemoryEntry:
    return MemoryEntry(content=content, memory_type=memory_type, source=source, **kwargs)


# ── MemoryEntry & Enums ──────────────────────────────────────────────────


class TestMemoryEntry:
    def test_creation_with_defaults(self):
        entry = _make_entry()
        assert entry.content == "test memory"
        assert entry.memory_type == MemoryType.EPISODE
        assert entry.source == MemorySource.USER
        assert entry.id is not None
        assert entry.embedding is None

    def test_immutability(self):
        entry = _make_entry()
        with pytest.raises(AttributeError):
            entry.content = "changed"

    def test_to_dict_roundtrip(self):
        entry = _make_entry(content="roundtrip test", memory_type=MemoryType.FACT)
        d = entry.to_dict()
        assert d["memory_type"] == "fact"
        restored = MemoryEntry.from_dict(d)
        assert restored.content == "roundtrip test"
        assert restored.memory_type == MemoryType.FACT

    def test_enum_values_are_strings(self):
        assert MemoryType.EPISODE.value == "episode"
        assert MemorySource.CONSOLIDATION.value == "consolidation"
        assert SourceTier.VECTOR.value == "vector"


# ── ShortTermMemory ──────────────────────────────────────────────────────


class TestShortTermMemory:
    def test_add_and_get_recent(self):
        stm = ShortTermMemory(max_turns=5)
        for i in range(3):
            stm.add(_make_entry(content=f"turn {i}"))
        recent = stm.get_recent(2)
        assert len(recent) == 2
        assert recent[-1].content == "turn 2"

    def test_overflow_eviction(self):
        stm = ShortTermMemory(max_turns=3)
        for i in range(4):
            evicted = stm.add(_make_entry(content=f"turn {i}"))
        assert evicted is not None
        assert evicted.content == "turn 0"
        assert stm.count() == 3

    def test_clear_returns_entries(self):
        stm = ShortTermMemory()
        stm.add(_make_entry(content="a"))
        stm.add(_make_entry(content="b"))
        cleared = stm.clear()
        assert len(cleared) == 2
        assert stm.count() == 0

    def test_keyword_search(self):
        stm = ShortTermMemory()
        stm.add(_make_entry(content="Python programming"))
        stm.add(_make_entry(content="JavaScript coding"))
        stm.add(_make_entry(content="Python data science"))
        results = stm.search("python")
        assert len(results) == 2


# ── LongTermMemory (SQLite) ──────────────────────────────────────────────


class TestLongTermMemory:
    def test_store_and_retrieve(self, tmp_path):
        ltm = LongTermMemory(db_path=tmp_path / "test.db")
        ltm.initialize()
        try:
            entry = _make_entry(content="long term fact", memory_type=MemoryType.FACT)
            ltm.store(entry)
            results = ltm.search_by_keyword("fact")
            assert len(results) == 1
            assert results[0].content == "long term fact"
            assert results[0].memory_type == MemoryType.FACT
        finally:
            ltm.dispose()

    def test_get_by_type(self, tmp_path):
        ltm = LongTermMemory(db_path=tmp_path / "test.db")
        ltm.initialize()
        try:
            ltm.store(_make_entry(content="fact 1", memory_type=MemoryType.FACT))
            ltm.store(_make_entry(content="profile 1", memory_type=MemoryType.PROFILE))
            facts = ltm.get_by_type(MemoryType.FACT)
            assert len(facts) == 1
            assert facts[0].memory_type == MemoryType.FACT
        finally:
            ltm.dispose()

    def test_count_and_delete(self, tmp_path):
        ltm = LongTermMemory(db_path=tmp_path / "test.db")
        ltm.initialize()
        try:
            entry = _make_entry(content="to delete")
            ltm.store(entry)
            assert ltm.count() == 1
            ltm.delete(entry.id)
            assert ltm.count() == 0
        finally:
            ltm.dispose()

    def test_lifecycle_dispose_closes_connection(self, tmp_path):
        ltm = LongTermMemory(db_path=tmp_path / "test.db")
        ltm.initialize()
        ltm.dispose()
        assert ltm._conn is None


# ── InMemoryVectorStore ──────────────────────────────────────────────────


class TestInMemoryVectorStore:
    def test_add_and_search(self):
        store = InMemoryVectorStore()
        store.add("v1", [1.0, 0.0, 0.0], {"type": "test"})
        store.add("v2", [0.0, 1.0, 0.0], {"type": "test"})
        results = store.search([1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0][0] == "v1"
        assert results[0][1] == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        score = InMemoryVectorStore._cosine_similarity([1, 0], [0, 1])
        assert score == pytest.approx(0.0)

    def test_delete_and_count(self):
        store = InMemoryVectorStore()
        store.add("v1", [1.0], {})
        store.add("v2", [2.0], {})
        assert store.count() == 2
        store.delete("v1")
        assert store.count() == 1

    def test_empty_search_returns_empty(self):
        store = InMemoryVectorStore()
        results = store.search([1.0, 0.0], top_k=5)
        assert results == []


# ── DeterministicEmbeddingProvider ───────────────────────────────────────


class TestDeterministicEmbeddingProvider:
    def test_deterministic_output(self):
        provider = DeterministicEmbeddingProvider(dim=64)
        v1 = provider.embed("hello world")
        v2 = provider.embed("hello world")
        assert v1 == v2  # Same text → same vector

    def test_different_text_different_vector(self):
        provider = DeterministicEmbeddingProvider(dim=64)
        v1 = provider.embed("hello")
        v2 = provider.embed("world")
        assert v1 != v2

    def test_correct_dimension(self):
        provider = DeterministicEmbeddingProvider(dim=128)
        v = provider.embed("test")
        assert len(v) == 128
        assert provider.dimension() == 128

    def test_batch_embed(self):
        provider = DeterministicEmbeddingProvider(dim=32)
        results = provider.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(len(v) == 32 for v in results)

    def test_values_in_range(self):
        provider = DeterministicEmbeddingProvider(dim=768)
        v = provider.embed("range test")
        assert all(-1.0 <= x <= 1.0 for x in v)


# ── MemoryService Integration ───────────────────────────────────────────


class TestMemoryService:
    @pytest.fixture
    def memory_service(self, tmp_path):
        from core.config.schemas import SystemConfig
        from dataclasses import replace as dc_replace
        from core.config.schemas import AppConfig, StorageConfig

        # Override storage path to tmp_path
        storage = StorageConfig(
            base_path=str(tmp_path),
            database_path=str(tmp_path / "database" / "eric.db"),
            vector_path=str(tmp_path / "vector"),
            logs_path=str(tmp_path / "logs"),
        )
        app = AppConfig(storage=storage)
        config = SystemConfig(app=app)

        from core.logger.factory import setup_logger
        logger = setup_logger(config.logging)
        from core.events import EventBus
        event_bus = EventBus()
        vector_store = InMemoryVectorStore()
        embedding = DeterministicEmbeddingProvider(dim=64)

        svc = MemoryService(
            config=config,
            logger=logger,
            event_bus=event_bus,
            vector_store=vector_store,
            embedding=embedding,
        )
        svc.initialize()
        yield svc
        svc.dispose()

    def test_store_and_get_recent(self, memory_service):
        entry = _make_entry(content="hello world")
        memory_service.store(entry)
        recent = memory_service.get_recent(5)
        assert len(recent) == 1
        assert recent[0].content == "hello world"

    def test_store_fact_persists_to_long_term(self, memory_service):
        fact = _make_entry(content="Python was created in 1991", memory_type=MemoryType.FACT)
        memory_service.store(fact)
        # Should be in both short-term and long-term
        recent = memory_service.get_recent(5)
        assert len(recent) == 1

    def test_clear_short_term(self, memory_service):
        memory_service.store(_make_entry(content="a"))
        memory_service.store(_make_entry(content="b"))
        memory_service.clear_short_term()
        assert memory_service.get_recent(10) == []


# ── MemoryModule DI Registration ─────────────────────────────────────────


class TestMemoryModule:
    def test_module_registers_all_interfaces(self):
        from core.di import Container
        from core.memory.module import MemoryModule

        container = Container()

        # Register required dependencies first
        from core.config.schemas import SystemConfig
        container.register_instance(SystemConfig, SystemConfig())

        from core.logger.factory import setup_logger
        logger = setup_logger({})
        from core.logger.interface import ILogger
        container.register_instance(ILogger, logger)

        from core.events import EventBus
        container.add_singleton(EventBus)

        # Register memory module
        MemoryModule().register(container)

        # Verify all interfaces are registered
        assert container.has(IEmbeddingProvider)
        assert container.has(IVectorStore)
        assert container.has(IMemoryService)
