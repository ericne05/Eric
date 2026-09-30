"""
core/approval/interfaces.py — Human-in-the-Loop Approval Interfaces.

Defines the abstract contracts for approval policy evaluation and management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Mapping, Optional

from core.approval.enums import ApprovalRiskLevel, ApprovalStatus
from core.approval.models import ApprovalEvaluation, ApprovalRequest


class IApprovalPolicy(ABC):
    """
    Contract for evaluating whether an action or tool call requires human approval.
    """

    @abstractmethod
    def evaluate(
        self,
        action_name: str,
        parameters: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ApprovalEvaluation:
        """
        Evaluate an action and determine if it requires explicit user approval.
        """
        pass


class IApprovalManager(ABC):
    """
    Contract for managing human-in-the-loop approval requests and enforcement.
    """

    @abstractmethod
    def evaluate_action(
        self,
        action_name: str,
        parameters: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ApprovalEvaluation:
        """Evaluate if an action requires approval."""
        pass

    @abstractmethod
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
        Register an approval request, notify clients, and wait asynchronously
        until approved, denied, cancelled, or expired.

        Returns:
            ApprovalStatus: The final decision status (APPROVED, DENIED, CANCELLED, or EXPIRED).
        """
        pass

    @abstractmethod
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Return all approval requests currently in PENDING status."""
        pass

    @abstractmethod
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Fetch an approval request by its unique ID."""
        pass

    @abstractmethod
    async def approve(self, request_id: str) -> bool:
        """
        Approve a pending request.

        Returns True if transitioned from PENDING to APPROVED.
        Returns False if request is not pending (already decided).
        Raises KeyError if request_id does not exist.
        """
        pass

    @abstractmethod
    async def deny(self, request_id: str) -> bool:
        """
        Deny a pending request.

        Returns True if transitioned from PENDING to DENIED.
        Returns False if request is not pending (already decided).
        Raises KeyError if request_id does not exist.
        """
        pass

    @abstractmethod
    def cancel_all_pending(self) -> int:
        """
        Cancel all currently pending requests to prevent shutdown deadlocks.
        Wakes any waiting execution tasks with CANCELLED status.

        Returns the number of cancelled requests.
        """
        pass
