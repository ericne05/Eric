# Architecture Specification — Eric v1.0 Agent Framework

**Version**: `1.0.0` (Stable API Freeze)  
**Runtime Engine**: Python ≥ 3.14  
**Architecture Paradigm**: Event-Driven, Multi-Runtime Goal-Oriented Autonomous Agent Framework

---

## 🏛️ Overall System Architecture

```text
                                  +-----------------------+
                                  |      User / Chat      |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |  GoalSpecification    |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |     Goal Manager      | <--- ExecutionContext (Pause/Resume)
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |  Autonomous Planner   | <--- GoalCostEstimator
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  | Capability Negotiator |
                                  +-----------+-----------+
                                              |
               +------------------------------+------------------------------+
               |                              |                              |
               v                              v                              v
    +--------------------+         +--------------------+         +--------------------+
    |  Browser Runtime   |         |  Desktop Runtime   |         |   Vision Runtime   |
    | (Playwright/Chrome)|         | (Windows 11 Native)|         | (OCR / ScreenGraph)|
    +----------+---------+         +----------+---------+         +----------+---------+
               |                              |                              |
               +------------------------------+------------------------------+
                                              |
                                              v
                                  +-----------------------+
                                  |  Telemetry Dashboard  |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |     Goal Artifact     |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |   Memory Intelligence |
                                  +-----------------------+
```

---

## 🔄 End-to-End Execution Sequence

```text
User            GoalManager        AutonomousPlanner    CapabilityNegotiator    Target Runtime        Telemetry
 |                   |                     |                    |                     |                   |
 |-- Create Goal --->|                     |                    |                     |                   |
 |                   |-- Decompose Spec -->|                    |                     |                   |
 |                   |<-- SubGoal DAG -----|                    |                     |                   |
 |                   |-- Build Plan ------>|                    |                     |                   |
 |                   |<-- ExecutionPlan ---|                    |                     |                   |
 |                   |                                          |                     |                   |
 |                   |-- Resolve Capability Requirement ------->|                     |                   |
 |                   |<-- Return Matching Runtime --------------|                     |                   |
 |                   |                                                                |                   |
 |                   |--------------------- Execute Step ---------------------------->|                   |
 |                   |<-------------------- Step Result ------------------------------|                   |
 |                   |                                                                                    |
 |                   |--------------------- Publish Event (goal.step.completed) ------------------------->|
 |                   |                                                                                    |
 |                   |-- Create Goal Artifact ----------------------------------------------------------->|
 |                   |                                                                                    |
 |<-- Goal Completed-|                                                                                    |
```

---

## 🔒 Stable API v1.0 Contract Declarations

The following core interfaces are locked under `API_VERSION = "1.0.0"`:

| Interface | File | Description |
|---|---|---|
| `IRuntime` | `core/runtime/interfaces.py` | Unified lifecycle for all runtimes (`start`, `observe`, `plan`, `execute`, `recover`, `shutdown`) |
| `IGoalManager` | `core/goals/interfaces.py` | High-level goal orchestration controller |
| `IGoalPlanner` | `core/goals/interfaces.py` | SubGoal DAG decomposition and plan builder |
| `IReplanner` | `core/goals/interfaces.py` | Dynamic replanning strategy on step failure |
| `ICostEstimator` | `core/goals/interfaces.py` | Pre-execution budget calculation |
| `CapabilityNegotiator` | `core/runtime/capability.py` | Dynamic runtime capability discovery and routing |
| `ExecutionContext` | `core/goals/managers/execution_context.py` | State snapshot persistence for Pause/Resume |
| `TelemetryDashboard` | `core/telemetry/dashboard.py` | Real-time passive system telemetry snapshotter |
