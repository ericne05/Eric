# Eric Engineering Handoff

> **Version:** Sprint 3 Completed  
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

---

## 🎯 2. Current Task: Sprint 4 — Config Loader Nâng Cao

### Goals:
1. Create branch `feature/sprint-4-config-loader` from `develop`.
2. Build `core/config/` for type-safe schema access (`config.app.name` instead of raw `dict` index).
3. Validate schemas and defaults for 10 YAML files in `configs/`.
4. Integrate `ConfigLoader` into `Bootstrap` and `Kernel`.

### Definition of Done (DoD):
- [ ] No raw `dict` or string indexing scattered across Kernel/Core.
- [ ] Schema validation implemented via Dataclass / Pydantic schemas.
- [ ] All 39 existing unit tests pass 100%.
- [ ] At least 10 new unit tests added in `tests/unit/test_config.py`.
- [ ] Update `docs/PROJECT_STATUS.md` and `docs/CHANGELOG.md`.

---

## ❌ 3. Out of Scope for Sprint 4

In Sprint 4, AI agents MUST NOT:
- ❌ Modify `EventBus` or `Event` schema.
- ❌ Modify `ILogger` or `LoggerManager`.
- ❌ Modify approved ADRs.
- ❌ Add UI, Brain, Agent, or Plugin logic.
- ❌ Add unauthorized third-party dependencies.

---

## 📌 Operational Status Footer

- **Current Sprint:** Sprint 4 (Config Loader Nâng Cao)
- **Git Branch:** `feature/sprint-4-config-loader`
- **Next Sprint:** Sprint 5 — Dependency Injection Container
- **Last Updated:** 2026-07-22
