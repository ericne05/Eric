"""
Tool Executor Implementation.
"""

import asyncio
from typing import Any, TYPE_CHECKING

from core.events.event import Event
from core.security.enums import PolicyDecision
from core.security.interfaces import IPolicyEngine
from core.telemetry.interfaces import ITelemetryManager
from core.tools.enums import ToolStatus
from core.tools.interfaces import IToolExecutor, IToolRegistry
from core.tools.models import ToolResult

if TYPE_CHECKING:
    from core.agents.interfaces import ExecutionContext


class ToolExecutor(IToolExecutor):
    """
    Standard implementation of IToolExecutor.
    Handles permissions, timeout, retry, policy, and event tracking.
    """

    def __init__(
        self,
        registry: IToolRegistry,
        policy_engine: IPolicyEngine,
        telemetry: ITelemetryManager,
        approval_manager: Any = None,
    ):
        self._registry = registry
        self._policy = policy_engine
        self._telemetry = telemetry
        self._approval_manager = approval_manager

    async def execute_tool(self, context: "ExecutionContext", fqn: str, cancellation_token: "CancellationToken | None" = None, **kwargs) -> ToolResult:
        self._telemetry.record_event("tool_execution_started", {"fqn": fqn, "trace_id": context.task.trace_id})
        
        tool = self._registry.get_tool(fqn)
        
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                error_message=f"Tool '{fqn}' not found in registry."
            )

        context.logger.info(f"[ToolExecutor] Executing '{fqn}' for Task {context.task.id}...")

        # 2. Execution with Timeout
        # Policy evaluation
        policy_result = self._policy.evaluate_action(tool, context)
        if policy_result.decision == PolicyDecision.DENY:
            context.logger.warning(f"[ToolExecutor] Policy denied tool '{fqn}': {policy_result.reason}")
            self._telemetry.record_event("tool_execution_denied", {"fqn": fqn, "reason": policy_result.reason})
            return ToolResult(status=ToolStatus.ERROR, error_message=f"Policy Denied: {policy_result.reason}")

        # Human-in-the-Loop Approval Gate (Sprint 18.5)
        if self._approval_manager:
            from core.approval.enums import ApprovalStatus
            metadata = {
                "tool": tool,
                "requires_approval": getattr(tool.schema, "requires_approval", False),
                "risk_level": getattr(tool.schema, "risk_level", "normal"),
                "category": getattr(tool.schema, "category", "general"),
                "permissions": getattr(tool.schema, "permissions", []),
                "description": getattr(tool.schema, "description", ""),
            }
            eval_res = self._approval_manager.evaluate_action(fqn, parameters=kwargs, metadata=metadata)
            if eval_res.requires_approval or policy_result.decision == PolicyDecision.ASK_USER:
                reason = eval_res.reason or policy_result.reason or f"Action '{fqn}' requires human approval."
                context.logger.info(f"[ToolExecutor] Action '{fqn}' requires approval: {reason}")
                decision = await self._approval_manager.request_and_wait(
                    action_name=fqn,
                    description=getattr(tool.schema, "description", f"Execute tool {fqn}"),
                    reason=reason,
                    risk_level=eval_res.risk_level,
                    parameters=kwargs,
                )
                if decision != ApprovalStatus.APPROVED:
                    context.logger.warning(f"[ToolExecutor] Tool '{fqn}' was {decision.value} by approval gate.")
                    self._telemetry.record_event("tool_execution_denied", {"fqn": fqn, "reason": f"Approval {decision.value}"})
                    return ToolResult(
                        status=ToolStatus.PERMISSION_DENIED,
                        error_message=f"Action '{fqn}' was {decision.value} by user approval.",
                    )

        timeout = tool.schema.timeout_seconds
        
        try:
            # We use asyncio.wait_for for timeout handling on async execution
            # If there's a cancellation token, we can't easily cancel wait_for if it's not checked inside, 
            # but we can check before starting.
            if cancellation_token and cancellation_token.is_cancelled:
                return ToolResult(status=ToolStatus.ERROR, error_message=cancellation_token.reason)

            # We use wait_for for timeout
            result = await asyncio.wait_for(
                tool.execute_async(context, cancellation_token=cancellation_token, **kwargs),
                timeout=timeout
            )
            
            self._telemetry.record_event("tool_execution_completed", {"fqn": fqn, "status": result.status.value})
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Tool '{fqn}' execution timed out after {timeout} seconds."
            context.logger.warning(f"[ToolExecutor] {error_msg}")
            
            context.event_bus.publish_sync(
                Event.create(
                    name="tool.timeout",
                    source="tool_executor",
                    payload={"fqn": fqn, "task_id": context.task.id}
                )
            )
            
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Tool '{fqn}' raised exception: {str(e)}"
            context.logger.exception(f"[ToolExecutor] {error_msg}")
            
            context.event_bus.publish_sync(
                Event.create(
                    name="tool.failed",
                    source="tool_executor",
                    payload={"fqn": fqn, "task_id": context.task.id, "error": str(e)}
                )
            )
            
            return ToolResult(
                status=ToolStatus.ERROR,
                error_message=error_msg
            )
