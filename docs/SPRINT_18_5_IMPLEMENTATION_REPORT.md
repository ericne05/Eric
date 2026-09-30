# Sprint 18.5 Implementation Report — Human-in-the-Loop Action Approval

## Executive Summary

Sprint 18.5 establishes a production-grade Human-in-the-Loop approval mechanism for consequential, destructive, and high-impact actions across the Eric Windows Desktop Assistant.

Approval is enforced as a **runtime safety boundary** at the core execution gates (`ToolExecutor` for agent tool calls and `GoalOrchestrator` for goal steps), rather than being merely a client-side UI confirmation dialog. All approval requests and decisions are transport-safe, preserving the strict `EricClient → IEricRuntime → EricRuntimeHost` architectural boundary without leaking live execution primitives or backend objects.

---

## Architecture & Conceptual Flow

```text
Goal / Agent
     ↓
Planned Action / Tool Call
     ↓
Approval Policy (DefaultApprovalPolicy)
     ↓
Does this action require approval?
     ├── NO → Execute side-effect immediately
     │
     └── YES
           ↓
     ApprovalManager creates ApprovalRequest (status: PENDING)
           ↓
     Emits 'approval.requested' (EventBus + IEricRuntime RuntimeEvent)
           ↓
     Execution PAUSES on asyncio.Event waiter (no busy-waiting)
           ↓
     EricClient.get_pending_approvals()
           ↓
     Client / Presentation Layer (GUI / CLI / Test)
           ↓
     EricClient.approve(request_id)  OR  EricClient.deny(request_id)
           ↓
     IEricRuntime → EricRuntimeHost → ApprovalManager
           ↓
     ├── APPROVE: Request status -> APPROVED; waiter released; action runs EXACTLY ONCE
     └── DENY:    Request status -> DENIED; waiter released; action aborts cleanly
```

---

## Subsystem Components

### 1. `core/approval/enums.py`
- `ApprovalStatus`: `PENDING`, `APPROVED`, `DENIED`, `CANCELLED`, `EXPIRED`
- `ApprovalRiskLevel`: `LOW`, `NORMAL`, `HIGH`, `CRITICAL`

### 2. `core/approval/models.py`
- `ApprovalEvaluation`: Result of policy evaluation (`requires_approval: bool`, `reason: str`, `risk_level: ApprovalRiskLevel`).
- `ApprovalRequest`: Transport-safe, frozen dataclass with primitive attributes:
  - `request_id`: Opaque string identifier (`req-xxxxxxxxxxxx`).
  - `action_name`: Tool or step action identifier (e.g. `filesystem.delete_file`).
  - `description`: Human-readable summary.
  - `reason`: Why confirmation is required.
  - `risk_level`: Severity enum.
  - `goal_id`: Optional associated goal ID.
  - `created_at`: UTC timestamp.
  - `status`: Lifecycle enum.
  - `parameters`: Transport-safe dictionary snapshot of parameters.
  - `to_dict()` and `from_dict()` for cross-process and client serialization.

### 3. `core/approval/interfaces.py`
- `IApprovalPolicy`: Interface for evaluating action approval requirements.
- `IApprovalManager`: Interface for managing requests, waiting, approving, denying, and cancelling.

### 4. `core/approval/policy.py` (`DefaultApprovalPolicy`)
- Classification rules:
  - **Exempt (Safe / Read-Only)**: `read_*`, `get_*`, `list_*`, `search_*`, `observe_*`, `screenshot`, `check_*`, `inspect_*`, `query_*`, `fetch_*`, `click`, `type_text`, `hotkey`, `drag`, `launch_application`.
  - **Consequential (Requires Approval)**:
    - **CRITICAL**: System power changes (`shutdown`, `reboot`), registry/startup modifications (`modify_registry`, `set_startup`, `format_drive`), financial transactions (`purchase`, `payment`, `transfer_funds`).
    - **HIGH**: Deletion (`delete`, `remove`, `unlink`, `rmdir`, `erase`, `wipe`), overwriting (`overwrite`, `truncate`), software management (`install`, `uninstall`), command execution (`exec_command`, `shell`, `cmd`, `powershell`), external messages (`send_message`, `send_email`).
  - **Metadata Overrides**: `ToolSchema.requires_approval` or action metadata `requires_approval=True`.
  - **Custom Rules**: `set_action_approval(action_name, requires_approval, reason, risk_level)`.

### 5. `core/approval/manager.py` (`ApprovalManager`)
- Coordinates pending requests and async waiter events.
- Guarantees **exactly-once execution safety**: once transitioned out of `PENDING`, subsequent `approve()` or `deny()` calls return `False` and do not re-trigger execution.
- Deterministic error handling: approving or denying an unknown `request_id` raises `KeyError`.
- Emits structured events (`approval.requested`, `approval.approved`, `approval.denied`, `approval.cancelled`) to `EventBus`.
- Shutdown safety: `cancel_all_pending()` safely unblocks all waiting executions with `CANCELLED` status so runtime host shutdown never deadlocks.

---

## Enforcement Locations

To ensure callers cannot trivially bypass approval:

1. **`ToolExecutor` (`core/tools/executor.py`)**:
   - Evaluates all tool executions against `ApprovalManager`.
   - If required, pauses and awaits decision.
   - If denied/cancelled, returns `ToolResult(status=ToolStatus.PERMISSION_DENIED, error_message=...)` without executing the underlying tool.

2. **`GoalOrchestrator` (`core/goals/orchestrator.py`)**:
   - Evaluates all plan execution steps before dispatching to runtimes.
   - If required, pauses and awaits decision.
   - If denied/cancelled, returns `{"success": False, "error": ..., "denied": True}` without invoking `runtime_instance.execute()`.

---

## Client / Runtime Boundary

Clients never interact directly with `ApprovalManager` or `EventBus`:

```text
UI / Presentation / Test
         │
         ▼
     EricClient
         │   .get_pending_approvals() -> List[ApprovalRequest]
         │   .approve(request_id) -> bool
         │   .deny(request_id) -> bool
         │   .subscribe("approval.*", handler)
         ▼
    IEricRuntime
         │
         ▼
   EricRuntimeHost
         │
         ▼
   ApprovalManager
```

---

## Shutdown & Restart Safety

- **No Live Object Persistence**: Neither `asyncio.Event`, `Future`, `Task`, `coroutine`, nor `ITool` instances are serialized.
- **Restart Independence**: A restarted process starts with zero pending live approvals and never assumes a previously pending request was approved.
- **Shutdown Cleanliness**: `EricRuntimeHost.stop()` calls `ApprovalManager.cancel_all_pending()` prior to runtime teardown, ensuring zero deadlocks.

---

## Test Verification Summary

- **Targeted Unit Tests**: 23 passed (`tests/unit/test_sprint18_5_approval.py`).
- **All Sprint 18 Tests**: 99 passed (18.1: 17, 18.2: 14, 18.3: 14, 18.4: 31, 18.5: 23).
- **Full Suite**: Zero new test failures introduced compared to the 371 passed / 2 failed baseline.
