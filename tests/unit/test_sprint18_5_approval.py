"""
tests/unit/test_sprint18_5_approval.py

Sprint 18.5 — Human-in-the-Loop Approval Tests.

Coverage:
    - Policy classification:
        * safe/read-only actions bypass approval
        * consequential actions (delete, overwrite, install, system commands, payment) require approval
        * tool metadata requires_approval=True triggers approval
        * custom rules override policy
    - Approval request creation:
        * unique request_id
        * pending status
        * transport-safe snapshot / to_dict / from_dict
    - Approve decision:
        * pending -> approved
        * protected action executes
        * exactly-once execution safety
    - Deny decision:
        * pending -> denied
        * protected action does NOT execute
    - Duplicate decision safety:
        * approving twice returns False on second call and does not re-execute
        * denied request cannot later become approved
        * approved request cannot later become denied
    - Unknown request ID:
        * predictable KeyError on approve/deny
    - Event emission:
        * approval.requested emitted with transport-safe payload
        * approval.approved emitted
        * approval.denied emitted
        * approval.cancelled emitted
    - Client / Runtime boundary:
        * EricClient -> IEricRuntime -> EricRuntimeHost -> ApprovalManager
        * client can get_pending_approvals, approve, deny
    - ToolExecutor enforcement:
        * protected tool pauses and requires approval
        * approving executes tool
        * denying returns ToolStatus.PERMISSION_DENIED without running tool
    - GoalOrchestrator enforcement:
        * protected goal step pauses and requires approval
        * approving executes step
        * denying aborts step with error
    - Shutdown safety:
        * pending approvals do not deadlock EricRuntimeHost.stop()
        * cancel_all_pending releases waiting execution tasks with CANCELLED status
    - Restart safety:
        * pending approvals never treated as approved across instances
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client.eric_client import EricClient
from core.approval.enums import ApprovalRiskLevel, ApprovalStatus
from core.approval.interfaces import IApprovalManager, IApprovalPolicy
from core.approval.manager import ApprovalManager
from core.approval.models import ApprovalEvaluation, ApprovalRequest
from core.approval.policy import DefaultApprovalPolicy
from core.events.event_bus import EventBus
from core.goals.models import ExecutionStep
from core.goals.orchestrator import GoalOrchestrator
from core.runtime.capability import CapabilityNegotiator
from core.runtime.client_interface import IEricRuntime
from core.runtime.host import EricRuntimeHost
from core.runtime.models import RuntimeEvent
from core.tools.decorator import tool
from core.tools.enums import ToolStatus
from core.tools.executor import ToolExecutor
from core.tools.models import ToolResult, ToolSchema
from core.tools.registry import ToolRegistry


# ── 1. Policy Tests ──────────────────────────────────────────────────────────


class TestApprovalPolicy:
    def test_safe_read_only_actions_bypass_approval(self):
        """Read-only and inspection actions must not require approval."""
        policy = DefaultApprovalPolicy()
        safe_actions = [
            "read_file",
            "get_status",
            "list_directory",
            "search_files",
            "observe_screen",
            "screenshot",
            "inspect_window",
            "query_database",
            "fetch_url",
            "click",
            "type_text",
            "hotkey",
            "launch_application",
        ]
        for action in safe_actions:
            res = policy.evaluate(action)
            assert res.requires_approval is False, f"Action '{action}' should NOT require approval"

    def test_consequential_actions_require_approval(self):
        """Destructive and consequential actions must require approval."""
        policy = DefaultApprovalPolicy()
        consequential_actions = [
            ("delete_file", ApprovalRiskLevel.HIGH),
            ("remove_directory", ApprovalRiskLevel.HIGH),
            ("erase_disk", ApprovalRiskLevel.HIGH),
            ("format_drive", ApprovalRiskLevel.CRITICAL),
            ("overwrite_config", ApprovalRiskLevel.HIGH),
            ("install_package", ApprovalRiskLevel.HIGH),
            ("uninstall_app", ApprovalRiskLevel.HIGH),
            ("system_shutdown", ApprovalRiskLevel.CRITICAL),
            ("reboot_system", ApprovalRiskLevel.CRITICAL),
            ("modify_registry", ApprovalRiskLevel.CRITICAL),
            ("exec_command", ApprovalRiskLevel.HIGH),
            ("run_command", ApprovalRiskLevel.HIGH),
            ("powershell_script", ApprovalRiskLevel.HIGH),
            ("send_message", ApprovalRiskLevel.HIGH),
            ("send_email", ApprovalRiskLevel.HIGH),
            ("purchase_item", ApprovalRiskLevel.CRITICAL),
            ("transfer_funds", ApprovalRiskLevel.CRITICAL),
        ]
        for action, expected_risk in consequential_actions:
            res = policy.evaluate(action)
            assert res.requires_approval is True, f"Action '{action}' MUST require approval"
            assert res.risk_level == expected_risk, f"Action '{action}' expected risk {expected_risk}, got {res.risk_level}"

    def test_explicit_metadata_requires_approval(self):
        """Tool/action metadata with requires_approval=True overrides default safe names."""
        policy = DefaultApprovalPolicy()
        res = policy.evaluate(
            "read_sensitive_file",
            metadata={"requires_approval": True, "reason": "Confidential file", "risk_level": "critical"},
        )
        assert res.requires_approval is True
        assert res.risk_level == ApprovalRiskLevel.CRITICAL
        assert "Confidential file" in res.reason

    def test_custom_rule_override(self):
        """Explicitly added policy rules take priority."""
        policy = DefaultApprovalPolicy()
        policy.set_action_approval("custom_action", True, reason="Custom security policy", risk_level=ApprovalRiskLevel.HIGH)
        res = policy.evaluate("custom_action")
        assert res.requires_approval is True
        assert "Custom security policy" in res.reason

        policy.set_action_approval("delete_temp_cache", False, reason="Safe temp file deletion")
        res2 = policy.evaluate("delete_temp_cache")
        assert res2.requires_approval is False


# ── 2. Request Creation & Serialization Tests ────────────────────────────────


class TestApprovalRequestModel:
    def test_request_has_unique_id_and_pending_status(self):
        """ApprovalRequest initialized with unique id and PENDING status."""
        req = ApprovalRequest(
            request_id="req-12345",
            action_name="os.delete_file",
            description="Delete system file",
            reason="Destructive action",
            risk_level=ApprovalRiskLevel.HIGH,
        )
        assert req.request_id == "req-12345"
        assert req.status == ApprovalStatus.PENDING
        assert req.risk_level == ApprovalRiskLevel.HIGH
        assert isinstance(req.created_at, datetime)

    def test_transport_safe_dict_roundtrip(self):
        """ApprovalRequest converts cleanly to/from transport-safe dict."""
        now = datetime.now(timezone.utc)
        req = ApprovalRequest(
            request_id="req-abc",
            action_name="system.reboot",
            description="Reboot machine",
            reason="Maintenance",
            risk_level=ApprovalRiskLevel.CRITICAL,
            goal_id="goal-999",
            created_at=now,
            status=ApprovalStatus.PENDING,
            parameters={"force": True},
        )
        data = req.to_dict()
        assert isinstance(data, dict)
        assert data["request_id"] == "req-abc"
        assert data["status"] == "pending"
        assert data["risk_level"] == "critical"
        assert data["parameters"] == {"force": True}

        restored = ApprovalRequest.from_dict(data)
        assert restored.request_id == req.request_id
        assert restored.action_name == req.action_name
        assert restored.status == req.status
        assert restored.risk_level == req.risk_level
        assert restored.goal_id == req.goal_id
        assert restored.parameters == {"force": True}


# ── 3. Approve Decision & Exactly-Once Safety ────────────────────────────────


class TestApproveDecision:
    @pytest.mark.asyncio
    async def test_approve_wakes_waiting_execution(self):
        """Approving a pending request unblocks the waiter with APPROVED status."""
        mgr = ApprovalManager()
        executed = []

        async def action_coro():
            status = await mgr.request_and_wait(
                action_name="delete_files",
                description="Delete old logs",
                reason="Consequential file deletion",
                risk_level=ApprovalRiskLevel.HIGH,
            )
            if status == ApprovalStatus.APPROVED:
                executed.append("executed")
            return status

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.01)  # Yield to let task create request and wait

        pending = mgr.get_pending_requests()
        assert len(pending) == 1
        req_id = pending[0].request_id

        # Approve the request
        ok = await mgr.approve(req_id)
        assert ok is True

        result_status = await task
        assert result_status == ApprovalStatus.APPROVED
        assert executed == ["executed"]
        assert len(mgr.get_pending_requests()) == 0

    @pytest.mark.asyncio
    async def test_approve_twice_does_not_execute_twice(self):
        """Calling approve() multiple times is safe and returns False on subsequent calls."""
        mgr = ApprovalManager()
        executed_count = 0

        async def action_coro():
            nonlocal executed_count
            status = await mgr.request_and_wait("delete_user_data")
            if status == ApprovalStatus.APPROVED:
                executed_count += 1
            return status

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.01)

        req_id = mgr.get_pending_requests()[0].request_id
        first = await mgr.approve(req_id)
        second = await mgr.approve(req_id)
        third = await mgr.approve(req_id)

        assert first is True
        assert second is False
        assert third is False

        await task
        assert executed_count == 1


# ── 4. Deny Decision Tests ───────────────────────────────────────────────────


class TestDenyDecision:
    @pytest.mark.asyncio
    async def test_deny_prevents_protected_action_execution(self):
        """Denying a pending request unblocks the waiter with DENIED and side-effect does NOT run."""
        mgr = ApprovalManager()
        executed = []

        async def action_coro():
            status = await mgr.request_and_wait("format_c_drive")
            if status == ApprovalStatus.APPROVED:
                executed.append("SHOULD_NOT_RUN")
            return status

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.01)

        req_id = mgr.get_pending_requests()[0].request_id
        ok = await mgr.deny(req_id)
        assert ok is True

        result_status = await task
        assert result_status == ApprovalStatus.DENIED
        assert executed == []

    @pytest.mark.asyncio
    async def test_denied_request_cannot_later_be_approved(self):
        """Once a request is DENIED, calling approve() returns False and state remains DENIED."""
        mgr = ApprovalManager()

        async def action_coro():
            return await mgr.request_and_wait("destructive_action")

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.01)

        req_id = mgr.get_pending_requests()[0].request_id
        await mgr.deny(req_id)
        approve_res = await mgr.approve(req_id)
        assert approve_res is False

        await task
        req = mgr.get_request(req_id)
        assert req is not None
        assert req.status == ApprovalStatus.DENIED

    @pytest.mark.asyncio
    async def test_approved_request_cannot_later_be_denied(self):
        """Once a request is APPROVED, calling deny() returns False and state remains APPROVED."""
        mgr = ApprovalManager()

        async def action_coro():
            return await mgr.request_and_wait("action_x")

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.01)

        req_id = mgr.get_pending_requests()[0].request_id
        await mgr.approve(req_id)
        deny_res = await mgr.deny(req_id)
        assert deny_res is False

        await task
        req = mgr.get_request(req_id)
        assert req is not None
        assert req.status == ApprovalStatus.APPROVED


# ── 5. Unknown Request ID Tests ──────────────────────────────────────────────


class TestUnknownRequestHandling:
    @pytest.mark.asyncio
    async def test_approve_unknown_id_raises_key_error(self):
        """approve() with nonexistent request_id raises KeyError."""
        mgr = ApprovalManager()
        with pytest.raises(KeyError):
            await mgr.approve("nonexistent-req-id")

    @pytest.mark.asyncio
    async def test_deny_unknown_id_raises_key_error(self):
        """deny() with nonexistent request_id raises KeyError."""
        mgr = ApprovalManager()
        with pytest.raises(KeyError):
            await mgr.deny("nonexistent-req-id")


# ── 6. Event Emission Tests ──────────────────────────────────────────────────


class TestApprovalEvents:
    @pytest.mark.asyncio
    async def test_approval_requested_and_approved_events_emitted(self):
        """approval.requested and approval.approved events are published to EventBus."""
        event_bus = EventBus()
        mgr = ApprovalManager(event_bus=event_bus)
        received_events = []

        def listener(evt):
            received_events.append(evt)

        event_bus.subscribe("approval.*", listener)

        async def action_coro():
            return await mgr.request_and_wait("delete_file", reason="File deletion")

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.02)

        req_id = mgr.get_pending_requests()[0].request_id
        await mgr.approve(req_id)
        await task
        await asyncio.sleep(0.02)

        event_names = [e.name for e in received_events]
        assert "approval.requested" in event_names
        assert "approval.approved" in event_names

        # Verify transport-safe payload of approval.requested
        req_event = next(e for e in received_events if e.name == "approval.requested")
        assert req_event.payload["request_id"] == req_id
        assert req_event.payload["action_name"] == "delete_file"
        assert req_event.payload["status"] == "pending"

    @pytest.mark.asyncio
    async def test_approval_denied_event_emitted(self):
        """approval.denied event is published on EventBus."""
        event_bus = EventBus()
        mgr = ApprovalManager(event_bus=event_bus)
        received_events = []

        def listener(evt):
            received_events.append(evt)

        event_bus.subscribe("approval.denied", listener)

        async def action_coro():
            return await mgr.request_and_wait("drop_tables")

        task = asyncio.create_task(action_coro())
        await asyncio.sleep(0.02)

        req_id = mgr.get_pending_requests()[0].request_id
        await mgr.deny(req_id)
        await task
        await asyncio.sleep(0.02)

        assert len(received_events) == 1
        assert received_events[0].payload["request_id"] == req_id
        assert received_events[0].payload["status"] == "denied"


# ── 7. Client / Runtime Boundary Tests ───────────────────────────────────────


class TestClientRuntimeBoundary:
    @pytest.mark.asyncio
    async def test_client_approval_workflow_end_to_end(self):
        """EricClient can get_pending_approvals, approve, and deny through the runtime boundary."""
        runtime = EricRuntimeHost()
        await runtime.start()
        client = EricClient(runtime=runtime)

        received_events: List[RuntimeEvent] = []
        client.subscribe("approval.*", lambda e: received_events.append(e))

        # Direct approval request via runtime approval manager
        approval_mgr = runtime.approval_manager
        assert approval_mgr is not None

        async def execute_protected():
            return await approval_mgr.request_and_wait(
                action_name="install_tool",
                description="Install package",
                reason="Package installation requires approval",
                risk_level=ApprovalRiskLevel.HIGH,
            )

        task = asyncio.create_task(execute_protected())
        await asyncio.sleep(0.02)

        # 1. UI retrieves pending approvals via EricClient
        pending = client.get_pending_approvals()
        assert len(pending) == 1
        req = pending[0]
        assert req.action_name == "install_tool"
        assert req.status == ApprovalStatus.PENDING

        # 2. UI approves via EricClient
        ok = await client.approve(req.request_id)
        assert ok is True

        decision = await task
        assert decision == ApprovalStatus.APPROVED
        assert len(client.get_pending_approvals()) == 0

        await runtime.stop()

    @pytest.mark.asyncio
    async def test_client_deny_workflow_end_to_end(self):
        """EricClient can deny a request through the runtime boundary."""
        runtime = EricRuntimeHost()
        await runtime.start()
        client = EricClient(runtime=runtime)

        approval_mgr = runtime.approval_manager
        assert approval_mgr is not None

        async def execute_protected():
            return await approval_mgr.request_and_wait("reboot_system")

        task = asyncio.create_task(execute_protected())
        await asyncio.sleep(0.02)

        pending = client.get_pending_approvals()
        assert len(pending) == 1
        req_id = pending[0].request_id

        ok = await client.deny(req_id)
        assert ok is True

        decision = await task
        assert decision == ApprovalStatus.DENIED
        assert len(client.get_pending_approvals()) == 0

        await runtime.stop()


# ── 8. ToolExecutor Approval Enforcement Tests ───────────────────────────────


class TestToolExecutorEnforcement:
    @pytest.mark.asyncio
    async def test_tool_with_requires_approval_enforced_by_executor(self):
        """A tool marked with requires_approval=True pauses and executes only on approve."""
        registry = ToolRegistry()
        policy = MagicMock()
        policy.evaluate_action.return_value = MagicMock(decision="allow")
        telemetry = MagicMock()
        approval_mgr = ApprovalManager()

        executor = ToolExecutor(
            registry=registry,
            policy_engine=policy,
            telemetry=telemetry,
            approval_manager=approval_mgr,
        )

        tool_executed = []

        @tool(namespace="filesystem", name="delete_folder", requires_approval=True, risk_level="high")
        def delete_folder(context, path: str):
            tool_executed.append(path)
            return f"Deleted {path}"

        registry.register(delete_folder)

        context = MagicMock()
        context.task.id = "task-1"
        context.task.trace_id = "trace-1"

        # Execute tool in background task
        task = asyncio.create_task(
            executor.execute_tool(context, "filesystem.delete_folder", path="/tmp/test")
        )
        await asyncio.sleep(0.02)

        # Confirm request is pending and tool has NOT run
        pending = approval_mgr.get_pending_requests()
        assert len(pending) == 1
        assert tool_executed == []
        req_id = pending[0].request_id

        # Approve
        await approval_mgr.approve(req_id)
        res = await task

        assert res.status == ToolStatus.SUCCESS
        assert tool_executed == ["/tmp/test"]

    @pytest.mark.asyncio
    async def test_tool_denied_returns_permission_denied_status(self):
        """A tool denied by the user returns ToolStatus.PERMISSION_DENIED without executing."""
        registry = ToolRegistry()
        policy = MagicMock()
        policy.evaluate_action.return_value = MagicMock(decision="allow")
        telemetry = MagicMock()
        approval_mgr = ApprovalManager()

        executor = ToolExecutor(
            registry=registry,
            policy_engine=policy,
            telemetry=telemetry,
            approval_manager=approval_mgr,
        )

        tool_executed = []

        @tool(namespace="system", name="shutdown_pc", requires_approval=True)
        def shutdown_pc(context):
            tool_executed.append("shutdown")
            return "Shutdown initiated"

        registry.register(shutdown_pc)

        context = MagicMock()
        context.task.id = "task-2"
        context.task.trace_id = "trace-2"

        task = asyncio.create_task(executor.execute_tool(context, "system.shutdown_pc"))
        await asyncio.sleep(0.02)

        req_id = approval_mgr.get_pending_requests()[0].request_id
        await approval_mgr.deny(req_id)
        res = await task

        assert res.status == ToolStatus.PERMISSION_DENIED
        assert "denied by user approval" in res.error_message
        assert tool_executed == []


# ── 9. GoalOrchestrator Approval Enforcement Tests ───────────────────────────


class TestGoalOrchestratorEnforcement:
    @pytest.mark.asyncio
    async def test_consequential_goal_step_enforces_approval(self):
        """Consequential goal step ('delete_files') pauses and requires approval in GoalOrchestrator."""
        negotiator = MagicMock()
        negotiator.find_runtimes_supporting.return_value = ["desktop"]
        mock_runtime = AsyncMock()
        mock_runtime.execute.return_value = {"success": True}
        negotiator._runtimes = {"desktop": mock_runtime}

        approval_mgr = ApprovalManager()
        orchestrator = GoalOrchestrator(negotiator=negotiator, approval_manager=approval_mgr)

        step = ExecutionStep(
            action_name="delete_files",
            arguments={"path": "C:\\Windows\\System32\\fake"},
        )

        task = asyncio.create_task(orchestrator.execute_step(step))
        await asyncio.sleep(0.02)

        # Approval request created
        pending = approval_mgr.get_pending_requests()
        assert len(pending) == 1
        assert mock_runtime.execute.call_count == 0
        req_id = pending[0].request_id

        # Approve
        await approval_mgr.approve(req_id)
        res = await task

        assert res["success"] is True
        assert mock_runtime.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_denied_goal_step_aborts_without_runtime_execution(self):
        """Denied goal step returns success=False and does not call runtime."""
        negotiator = MagicMock()
        negotiator.find_runtimes_supporting.return_value = ["desktop"]
        mock_runtime = AsyncMock()
        negotiator._runtimes = {"desktop": mock_runtime}

        approval_mgr = ApprovalManager()
        orchestrator = GoalOrchestrator(negotiator=negotiator, approval_manager=approval_mgr)

        step = ExecutionStep(
            action_name="format_partition",
            arguments={"drive": "D:"},
        )

        task = asyncio.create_task(orchestrator.execute_step(step))
        await asyncio.sleep(0.02)

        req_id = approval_mgr.get_pending_requests()[0].request_id
        await approval_mgr.deny(req_id)
        res = await task

        assert res["success"] is False
        assert res.get("denied") is True
        assert mock_runtime.execute.call_count == 0


# ── 10. Shutdown & Restart Safety Tests ──────────────────────────────────────


class TestShutdownAndRestartSafety:
    @pytest.mark.asyncio
    async def test_pending_approval_does_not_deadlock_shutdown(self):
        """EricRuntimeHost.stop() cancels pending approvals and releases waiting tasks without deadlock."""
        runtime = EricRuntimeHost()
        await runtime.start()

        approval_mgr = runtime.approval_manager
        assert approval_mgr is not None

        execution_status = []

        async def waiting_action():
            status = await approval_mgr.request_and_wait("consequential_command")
            execution_status.append(status)
            return status

        action_task = asyncio.create_task(waiting_action())
        await asyncio.sleep(0.02)

        assert len(approval_mgr.get_pending_requests()) == 1

        # Stop runtime host — must complete promptly and release action_task
        await asyncio.wait_for(runtime.stop(), timeout=3.0)

        res = await asyncio.wait_for(action_task, timeout=1.0)
        assert res == ApprovalStatus.CANCELLED
        assert execution_status == [ApprovalStatus.CANCELLED]

    def test_restart_safety_fresh_manager_has_no_active_approvals(self):
        """A new process/instance starts with zero active approvals and never auto-executes."""
        fresh_mgr = ApprovalManager()
        assert len(fresh_mgr.get_pending_requests()) == 0
        assert len(fresh_mgr.get_all_requests()) == 0
