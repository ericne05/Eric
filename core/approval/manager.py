"""
core/approval/manager.py — Human-in-the-Loop Approval Manager.

Central runtime coordinator for action approvals.
Enforces pause-and-wait execution semantics, exactly-once approval safety,
timeout handling, EventBus notification, and clean shutdown cancellation.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from core.approval.enums import ApprovalRiskLevel, ApprovalStatus
from core.approval.interfaces import IApprovalManager, IApprovalPolicy
from core.approval.models import ApprovalEvaluation, ApprovalRequest
from core.approval.policy import DefaultApprovalPolicy
from core.events.event import Event
from core.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApprovalManager(IApprovalManager):
    """
    Production-grade Human-in-the-Loop Approval Manager.

    Owns approval requests, enforces pause before protected side-effects execute,
    manages asynchronous waiter events, dispatches approval events, and guarantees
    that shutdown never deadlocks on pending requests.
    """

    def __init__(
        self,
        policy: Optional[IApprovalPolicy] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._policy = policy or DefaultApprovalPolicy()
        self._event_bus = event_bus
        self._requests: Dict[str, ApprovalRequest] = {}
        self._waiters: Dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    def evaluate_action(
        self,
        action_name: str,
        parameters: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ApprovalEvaluation:
        """Evaluate an action against the configured approval policy."""
        return self._policy.evaluate(action_name, parameters=parameters, metadata=metadata)

    async def request_and_wait(
        self,
        action_name: str,
        description: str = "",
        reason: str = "",
        risk_level: ApprovalRiskLevel = ApprovalRiskLevel.NORMAL,
        goal_id: Optional[str] = None,
        parameters: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> ApprovalStatus:
        """
        Create a pending approval request, notify clients, and wait asynchronously
        until approved, denied, cancelled, or expired.
        """
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        safe_params = dict(parameters) if parameters else {}
        now = datetime.now(timezone.utc)

        waiter = asyncio.Event()

        async with self._lock:
            req = ApprovalRequest(
                request_id=request_id,
                action_name=action_name,
                description=description or f"Execute '{action_name}'",
                reason=reason or f"Action '{action_name}' requires confirmation.",
                risk_level=risk_level,
                goal_id=goal_id,
                created_at=now,
                status=ApprovalStatus.PENDING,
                parameters=safe_params,
            )
            self._requests[request_id] = req
            self._waiters[request_id] = waiter

        logger.info(
            "[ApprovalManager] Approval requested for '%s' (request_id=%s, risk=%s): %s",
            action_name,
            request_id,
            risk_level.value,
            reason,
        )

        # Emit approval.requested event
        await self._emit_event("approval.requested", req.to_dict())

        # Wait for decision or timeout
        try:
            if timeout and timeout > 0:
                await asyncio.wait_for(waiter.wait(), timeout=timeout)
            else:
                await waiter.wait()
        except asyncio.TimeoutError:
            logger.warning("[ApprovalManager] Request '%s' timed out; marking EXPIRED", request_id)
            async with self._lock:
                current_req = self._requests.get(request_id)
                if current_req and current_req.status == ApprovalStatus.PENDING:
                    self._requests[request_id] = ApprovalRequest(
                        request_id=current_req.request_id,
                        action_name=current_req.action_name,
                        description=current_req.description,
                        reason=current_req.reason,
                        risk_level=current_req.risk_level,
                        goal_id=current_req.goal_id,
                        created_at=current_req.created_at,
                        status=ApprovalStatus.EXPIRED,
                        parameters=current_req.parameters,
                    )
                    await self._emit_event("approval.cancelled", {
                        "request_id": request_id,
                        "action_name": current_req.action_name,
                        "reason": "expired",
                    })

        async with self._lock:
            self._waiters.pop(request_id, None)
            final_req = self._requests.get(request_id)
            final_status = final_req.status if final_req else ApprovalStatus.CANCELLED

        logger.info("[ApprovalManager] Decision for '%s': %s", request_id, final_status.value)
        return final_status

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Return all approval requests currently awaiting user decision."""
        return [
            req for req in self._requests.values()
            if req.status == ApprovalStatus.PENDING
        ]

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Fetch an approval request by its unique ID."""
        return self._requests.get(request_id)

    def get_all_requests(self) -> List[ApprovalRequest]:
        """Return all approval requests."""
        return list(self._requests.values())

    async def approve(self, request_id: str) -> bool:
        """
        Approve a pending request. Exactly-once safe.

        Returns True if transition occurred from PENDING to APPROVED.
        Returns False if request is not pending.
        Raises KeyError if request_id does not exist.
        """
        async with self._lock:
            if request_id not in self._requests:
                raise KeyError(f"Approval request '{request_id}' not found.")

            req = self._requests[request_id]
            if req.status != ApprovalStatus.PENDING:
                logger.warning(
                    "[ApprovalManager] approve() called on '%s' but status is already '%s'",
                    request_id,
                    req.status.value,
                )
                return False

            self._requests[request_id] = ApprovalRequest(
                request_id=req.request_id,
                action_name=req.action_name,
                description=req.description,
                reason=req.reason,
                risk_level=req.risk_level,
                goal_id=req.goal_id,
                created_at=req.created_at,
                status=ApprovalStatus.APPROVED,
                parameters=req.parameters,
            )
            waiter = self._waiters.get(request_id)
            if waiter:
                waiter.set()

        logger.info("[ApprovalManager] Request '%s' APPROVED", request_id)
        await self._emit_event("approval.approved", {
            "request_id": request_id,
            "action_name": req.action_name,
            "goal_id": req.goal_id,
            "status": ApprovalStatus.APPROVED.value,
        })
        return True

    async def deny(self, request_id: str) -> bool:
        """
        Deny a pending request.

        Returns True if transition occurred from PENDING to DENIED.
        Returns False if request is not pending.
        Raises KeyError if request_id does not exist.
        """
        async with self._lock:
            if request_id not in self._requests:
                raise KeyError(f"Approval request '{request_id}' not found.")

            req = self._requests[request_id]
            if req.status != ApprovalStatus.PENDING:
                logger.warning(
                    "[ApprovalManager] deny() called on '%s' but status is already '%s'",
                    request_id,
                    req.status.value,
                )
                return False

            self._requests[request_id] = ApprovalRequest(
                request_id=req.request_id,
                action_name=req.action_name,
                description=req.description,
                reason=req.reason,
                risk_level=req.risk_level,
                goal_id=req.goal_id,
                created_at=req.created_at,
                status=ApprovalStatus.DENIED,
                parameters=req.parameters,
            )
            waiter = self._waiters.get(request_id)
            if waiter:
                waiter.set()

        logger.info("[ApprovalManager] Request '%s' DENIED", request_id)
        await self._emit_event("approval.denied", {
            "request_id": request_id,
            "action_name": req.action_name,
            "goal_id": req.goal_id,
            "status": ApprovalStatus.DENIED.value,
        })
        return True

    def cancel_all_pending(self) -> int:
        """
        Cancel all currently pending requests to prevent shutdown deadlocks.
        Wakes any waiting execution tasks with CANCELLED status.
        """
        cancelled_count = 0
        for request_id, req in list(self._requests.items()):
            if req.status == ApprovalStatus.PENDING:
                self._requests[request_id] = ApprovalRequest(
                    request_id=req.request_id,
                    action_name=req.action_name,
                    description=req.description,
                    reason=req.reason,
                    risk_level=req.risk_level,
                    goal_id=req.goal_id,
                    created_at=req.created_at,
                    status=ApprovalStatus.CANCELLED,
                    parameters=req.parameters,
                )
                waiter = self._waiters.get(request_id)
                if waiter:
                    waiter.set()
                cancelled_count += 1
                logger.info("[ApprovalManager] Request '%s' cancelled during shutdown/cleanup", request_id)

        return cancelled_count

    async def _emit_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Dispatch structured event to EventBus if available."""
        if self._event_bus and hasattr(self._event_bus, "publish"):
            try:
                event = Event.create(
                    name=event_name,
                    source="approval.manager",
                    payload=payload,
                )
                await self._event_bus.publish(event)
            except Exception as exc:
                logger.debug("[ApprovalManager] EventBus publish for '%s' omitted: %s", event_name, exc)
