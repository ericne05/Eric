# Eric Engineering Handoff

> **Version:** Sprint 5 Completed  
> **Status:** Active Development (Phase 1 — Core Runtime)  
> **Activation Trigger Phrase:** `khởi động Eric`

---

## 🛑 READ ORDER (MANDATORY)

Before writing ANY code or taking action, read the following documents in order:

1. 📜 [CONSTITUTION.md](file:///D:/Projects/Eric/docs/CONSTITUTION.md) — 8 Immutable rules of Eric (Never bypass Kernel, Fail Fast...)
2. 📐 [DEPENDENCY_RULES.md](file:///D:/Projects/Eric/docs/DEPENDENCY_RULES.md) — Layer hierarchy and import rules (No circular imports)
3. 💡 [ENGINEERING_GUIDE.md](file:///D:/Projects/Eric/docs/ENGINEERING_GUIDE.md) — Coding philosophy, DI, testing strategy & docstrings
4. 📊 [PROJECT_STATUS.md](file:///D:/Projects/Eric/docs/PROJECT_STATUS.md) — Live status dashboard, test counts & test coverage

*Failure to follow these documents is considered a violation of the project architecture.*

---

## 🔒 1. Architecture Freeze (DO NOT MODIFY)

The following core foundation modules are **FROZEN**. Do NOT alter their public APIs without explicit user approval:

1. **Kernel Lifecycle (`core/kernel/`)**: 6-state ordered lifecycle (`CREATED` → `STOPPED`). Kernel wires modules in `boot()`.
2. **Event Bus (`core/events/`)**: Pub/Sub async/sync, pattern matching (`system.*`, `*`), `Event` dataclass `frozen=True`.
3. **Logger (`core/logger/`)**: `ILogger` interface abstraction, `LoggerManager`, `setup_logger`. Logger is "silent" (does NOT emit events).
4. **Config System (`core/config/`)**: `SystemConfig` frozen dataclass, `ConfigService` pipeline, `ConfigRegistry` for schema registration.
5. **DI Container (`core/di/`)**: `Container`, `Scope`, `Provider`, `IDependencyModule`, `ILifecycleAware`. Constructor Injection only. No Service Locator pattern — only Kernel/Bootstrap may call `resolve()`.

---

## 🎯 2. Current Task: Sprint 6 — Memory Engine

### Goals:
1. Create branch `feature/sprint-6-memory-engine` from `develop`.
2. Build `core/memory/` with `MemoryService`, embedding interfaces, vector store interfaces.
3. All services register via DI Container using `IDependencyModule`.
4. Constructor injection only — no `container.resolve()` outside Kernel/Bootstrap.

### Definition of Done (DoD):
- [ ] `MemoryService` registered as singleton via `MemoryModule`.
- [ ] `IVectorStore` and `IEmbeddingProvider` interfaces defined.
- [ ] All 80 existing unit tests pass 100%.
- [ ] At least 15 new unit tests added.
- [ ] Update `docs/PROJECT_STATUS.md` and `docs/CHANGELOG.md`.

---

## ❌ 3. Out of Scope for Sprint 6

In Sprint 6, AI agents MUST NOT:
- ❌ Modify `Container`, `Scope`, or `Provider` public APIs.
- ❌ Modify `EventBus` or `Event` schema.
- ❌ Modify `ILogger` or `LoggerManager`.
- ❌ Modify `SystemConfig` or `ConfigService`.
- ❌ Add UI, Brain, Agent, or Plugin logic.
- ❌ Add unauthorized third-party dependencies.
- ❌ Use `container.resolve()` outside of Kernel/Bootstrap.

---

## 📌 Operational Status Footer

- **Current Sprint:** Sprint 6 (Memory Engine)
- **Git Branch:** `feature/sprint-6-memory-engine`
- **Next Sprint:** Sprint 7 — Dynamic Plugin Loader
- **Last Updated:** 2026-07-24
