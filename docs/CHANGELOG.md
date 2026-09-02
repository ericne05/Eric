# CHANGELOG — Eric Personal AI Agent OS

All notable changes to the Eric project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
- Preparing Sprint 7 — Dynamic Plugin Loader.

---

## [0.6.0] - 2026-07-24 (Sprint 6)

### Added
- Complete Memory Engine architecture at `core/memory/`.
- `MemoryEntry` and `SearchResult` frozen dataclasses for immutable data transfer.
- Type-safe Enums: `MemoryType`, `MemorySource`, `SourceTier`.
- Interfaces for storage and embeddings: `IMemoryService`, `IVectorStore`, `IEmbeddingProvider`.
- `ShortTermMemory`: In-memory circular buffer for recent conversational context.
- `LongTermMemory`: SQLite-backed persistent store for facts, episodes, and profile.
- `InMemoryVectorStore`: Local, dependency-free vector store using Python cosine similarity for dev/test.
- `DeterministicEmbeddingProvider`: Reproducible SHA-256-based embeddings for stable testing.
- `RecallEngine`: Multi-tier search engine that queries short-term, long-term, and vector stores, then merges and ranks results.
- `MemoryService`: Unified facade for all memory operations, orchestrating the different tiers.
- 25 new unit tests covering all memory components (`tests/unit/test_memory.py`).

### Changed
- `Kernel` now registers `MemoryModule` via DI Container during `_init_container()`.

---

## [0.5.0] - 2026-07-24 (Sprint 5)

### Added
- Custom DI Container (`core/di/`) with auto constructor injection via Python type hints.
- Three lifetime strategies: `Singleton` (lazy), `Transient`, `Scoped`.
- Interface-based registration (`ILogger` → `LoggerManager`).
- Factory-based registration (`lambda c: ...`).
- DSL shortcuts: `add_singleton()`, `add_transient()`, `add_scoped()`, `register_instance()`.
- `ILifecycleAware` interface with `initialize()` / `dispose()` hooks.
- `IDependencyModule` interface for modular subsystem registration.
- Module registration co-located with each subsystem (`core/config/module.py`, `core/events/module.py`, `core/logger/module.py`).
- `Scope` class for scoped service lifetimes (child container pattern).
- Circular dependency detection with full resolution stack in error message.
- Optional dependency support (`Type | None = None` → injects `None` if unregistered).
- Primitive type skipping for constructor parameters with defaults.
- 30 new unit tests for DI subsystem (`tests/unit/test_di.py`).

### Changed
- Kernel boot sequence now flows through Container: `Container → Logger → EventBus → Ready`.
- `Kernel._init_container()` implemented (was `TODO`).
- `Kernel.shutdown()` calls `container.dispose()` for lifecycle cleanup.
- Logger and EventBus are now resolved from DI Container instead of direct instantiation.

---

## [0.4.0] - 2026-07-23 (Sprint 4)

### Added
- Advanced Config Loader System (Architecture 2.0) at `core/config/`.
- `ConfigRegistry` for dynamic plugin schema registration.
- 10 immutable `@dataclass(frozen=True)` configuration schemas.
- `EnvResolver` with `${ENV_VAR:default}` syntax.
- `ConfigService` pipeline: Parser → Resolver → Builder → Validator → Cache.
- `YAMLParser` and `JSONParser` for multi-format support.
- Custom exception hierarchy (`ConfigError`, `SchemaValidationError`, etc.).
- 21 new unit tests (`tests/unit/test_config.py`).

### Changed
- `Kernel` and `Bootstrap` now use `SystemConfig` (dataclass) instead of raw dict.
- `LoggerManager.configure()` accepts `LoggingConfig | dict`.

---

## [0.3.0] - 2026-07-22 (Sprint 3)

### Added
- Enterprise `ILogger` abstract interface (`core/logger/interface.py`).
- `LoggerManager` implementing `ILogger` wrapping loguru backend (`core/logger/manager.py`).
- Factory `setup_logger()` and `InterceptHandler` for standard library `logging` redirection (`core/logger/factory.py`).
- Console Sink (colored stdout) and Rotating File Sink (`storage/logs/eric.log`).
- Structured logging via `logger.bind(...)` for contextual tracing.
- 5 new unit tests in `tests/unit/test_logger.py` (39 total tests passing).

### Changed
- Integrated `ILogger` into Kernel lifecycle (`_init_logger`, `_shutdown_logger`).
- Removed 100% of temporary `print()` statements from `Kernel`.

---

## [0.2.0] - 2026-07-22 (Sprint 2)

### Added
- Standardized immutable `Event` dataclass with 7 fields (`id`, `name`, `source`, `timestamp`, `correlation_id`, `payload`, `metadata`).
- Pub/Sub `EventBus` supporting async/sync handlers, wildcard pattern matching (`system.*`, `*`), and handler exception isolation (`core/events/`).
- 17 new unit tests in `tests/unit/test_events.py` (34 total tests passing).

### Changed
- Integrated `EventBus` into `Kernel`, emitting `system.ready` on boot and `system.shutdown` on shutdown.

---

## [0.1.0] - 2026-07-22 (Sprint 1)

### Added
- Core Python 3.14 project structure.
- `Bootstrap` subsystem for `.env` loading, YAML configs parsing, and `${ENV_VAR}` expansion (`core/kernel/bootstrap.py`).
- `Kernel` subsystem managing 6-state ordered lifecycle (`CREATED` → `BOOTING` → `READY` → `RUNNING` → `SHUTTING_DOWN` → `STOPPED`).
- 17 initial unit tests for Bootstrap and Kernel (`tests/unit/test_bootstrap.py`, `tests/unit/test_kernel.py`).
