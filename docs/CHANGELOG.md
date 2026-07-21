# CHANGELOG — Eric Personal AI Agent OS

All notable changes to the Eric project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned for Sprint 4
- Config Loader module (`core/config/`) with Type-safe schemas and validation for 10 YAML files.

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
