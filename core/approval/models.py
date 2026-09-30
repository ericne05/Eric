"""
core/approval/models.py — Approval Request and Evaluation Models.

Defines transport-safe, serializable models for Human-in-the-Loop approvals.
Contains no live Python service objects, coroutines, tasks, or adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from core.approval.enums import ApprovalRiskLevel, ApprovalStatus


@dataclass(frozen=True)
class ApprovalEvaluation:
    """
    Result of evaluating an action against the approval policy.
    """
    requires_approval: bool
    reason: str = ""
    risk_level: ApprovalRiskLevel = ApprovalRiskLevel.NORMAL


@dataclass(frozen=True)
class ApprovalRequest:
    """
    Transport-safe approval request representing an action awaiting human decision.

    Guaranteed to contain only primitive/serializable fields.
    """
    request_id: str
    action_name: str
    description: str = ""
    reason: str = ""
    risk_level: ApprovalRiskLevel = ApprovalRiskLevel.NORMAL
    goal_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ApprovalStatus = ApprovalStatus.PENDING
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert approval request to a JSON-serializable dictionary."""
        return {
            "request_id": self.request_id,
            "action_name": self.action_name,
            "description": self.description,
            "reason": self.reason,
            "risk_level": self.risk_level.value,
            "goal_id": self.goal_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """Reconstruct from dictionary."""
        raw_status = data.get("status", ApprovalStatus.PENDING.value)
        status = ApprovalStatus(raw_status) if raw_status in ApprovalStatus._value2member_map_ else ApprovalStatus.PENDING

        raw_risk = data.get("risk_level", ApprovalRiskLevel.NORMAL.value)
        risk_level = ApprovalRiskLevel(raw_risk) if raw_risk in ApprovalRiskLevel._value2member_map_ else ApprovalRiskLevel.NORMAL

        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        return cls(
            request_id=data.get("request_id", ""),
            action_name=data.get("action_name", ""),
            description=data.get("description", ""),
            reason=data.get("reason", ""),
            risk_level=risk_level,
            goal_id=data.get("goal_id"),
            created_at=created_at,
            status=status,
            parameters=data.get("parameters", {}),
        )
