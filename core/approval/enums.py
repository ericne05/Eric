"""
core/approval/enums.py — Human-in-the-Loop Approval Enums.

Defines lifecycle statuses and risk classification for approval requests.
"""

from enum import Enum


class ApprovalStatus(str, Enum):
    """
    Lifecycle status of an ApprovalRequest.
    """
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalRiskLevel(str, Enum):
    """
    Risk severity classification for actions requiring approval.
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
