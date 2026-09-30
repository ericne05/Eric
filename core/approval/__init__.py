"""
core/approval — Human-in-the-Loop Approval Subsystem.

Public API:
    ApprovalStatus        — Request lifecycle states
    ApprovalRiskLevel     — Action risk severity
    ApprovalRequest       — Transport-safe approval request dataclass
    ApprovalEvaluation    — Policy evaluation outcome
    IApprovalPolicy       — Policy evaluation interface
    IApprovalManager      — Approval manager interface
    DefaultApprovalPolicy — Heuristic & rule-based approval policy
    ApprovalManager       — Production approval coordinator
"""

from core.approval.enums import ApprovalRiskLevel, ApprovalStatus
from core.approval.interfaces import IApprovalManager, IApprovalPolicy
from core.approval.manager import ApprovalManager
from core.approval.models import ApprovalEvaluation, ApprovalRequest
from core.approval.policy import DefaultApprovalPolicy

__all__ = [
    "ApprovalStatus",
    "ApprovalRiskLevel",
    "ApprovalRequest",
    "ApprovalEvaluation",
    "IApprovalPolicy",
    "IApprovalManager",
    "DefaultApprovalPolicy",
    "ApprovalManager",
]
