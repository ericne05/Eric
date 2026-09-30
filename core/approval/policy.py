"""
core/approval/policy.py — Default Approval Policy Implementation.

Distinguishes between low-impact/read-only operations and consequential/destructive actions.
Supports metadata-driven overrides, rule configuration, and capability classification.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional

from core.approval.enums import ApprovalRiskLevel
from core.approval.interfaces import IApprovalPolicy
from core.approval.models import ApprovalEvaluation


class DefaultApprovalPolicy(IApprovalPolicy):
    """
    Default policy classifying actions based on:
    1. Explicit metadata (e.g. requires_approval=True on ToolSchema)
    2. Explicit action rule overrides (exact match or prefix)
    3. Consequential vs safe keyword patterns
    """

    # Actions that are dangerous or consequential by default (CRITICAL evaluated first)
    _CONSEQUENTIAL_PATTERNS = [
        # System power and configuration (CRITICAL)
        (r"(^|[._])(shutdown|reboot|restart_system|format_drive|modify_registry|set_startup|disable_service)($|[._])",
         "Critical system configuration or power state change", ApprovalRiskLevel.CRITICAL),
        # Financial / transactions (CRITICAL)
        (r"(^|[._])(purchase|payment|buy|checkout|transfer_funds|charge)($|[._])",
         "Financial or commercial transaction", ApprovalRiskLevel.CRITICAL),
        # Deletion / destruction (HIGH)
        (r"(^|[._])(delete|remove|unlink|rmdir|erase|format|wipe|destroy|drop|purge)($|[._])",
         "Destructive deletion or removal of resources", ApprovalRiskLevel.HIGH),
        # Overwrite (HIGH)
        (r"(^|[._])(overwrite|truncate)($|[._])",
         "Overwriting existing files or data", ApprovalRiskLevel.HIGH),
        # Software management (HIGH)
        (r"(^|[._])(install|uninstall|update_system)($|[._])",
         "Installation or modification of software", ApprovalRiskLevel.HIGH),
        # Arbitrary command / code execution (HIGH)
        (r"(^|[._])(exec_command|run_command|shell|cmd|powershell|execute_script|run_script|eval)($|[._])",
         "Execution of arbitrary system commands", ApprovalRiskLevel.HIGH),
        # External communication with visible side-effects (HIGH)
        (r"(^|[._])(send_message|send_email|post_tweet|publish|broadcast|webhook_post)($|[._])",
         "External message or communication with side effects", ApprovalRiskLevel.HIGH),
    ]

    # Read-only or safe patterns that bypass approval by default
    _SAFE_PREFIXES = (
        "read", "get", "list", "search", "find", "observe", "screenshot",
        "check", "inspect", "query", "fetch", "scan", "count", "view",
        "mouse", "keyboard", "click", "double_click", "right_click",
        "type_text", "hotkey", "drag", "scroll", "launch", "open",
    )

    def __init__(self, default_require_approval: bool = False):
        self._default_require_approval = default_require_approval
        self._rules: Dict[str, ApprovalEvaluation] = {}

    def set_action_approval(
        self,
        action_name: str,
        requires_approval: bool,
        reason: str = "",
        risk_level: ApprovalRiskLevel = ApprovalRiskLevel.NORMAL,
    ) -> None:
        """Add an explicit rule for an action name."""
        self._rules[action_name] = ApprovalEvaluation(
            requires_approval=requires_approval,
            reason=reason or ("Explicitly configured to require approval" if requires_approval else "Explicitly allowed"),
            risk_level=risk_level,
        )

    def evaluate(
        self,
        action_name: str,
        parameters: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ApprovalEvaluation:
        metadata = metadata or {}
        norm_name = action_name.lower().strip()

        # 1. Explicit metadata override
        if metadata.get("requires_approval") is True:
            reason = metadata.get("reason") or metadata.get("approval_reason") or f"Action '{action_name}' is explicitly configured to require approval."
            raw_risk = metadata.get("risk_level", ApprovalRiskLevel.HIGH)
            risk = ApprovalRiskLevel(raw_risk) if raw_risk in ApprovalRiskLevel._value2member_map_ else ApprovalRiskLevel.HIGH
            return ApprovalEvaluation(requires_approval=True, reason=reason, risk_level=risk)

        # 2. Explicit rule match
        if action_name in self._rules:
            return self._rules[action_name]
        if norm_name in self._rules:
            return self._rules[norm_name]

        # 3. Explicit safe check if action starts with safe prefix and doesn't match dangerous keywords
        is_safe_prefix = any(norm_name.startswith(p) or f".{p}" in norm_name for p in self._SAFE_PREFIXES)

        # 4. Check consequential patterns
        for pattern, reason, risk_level in self._CONSEQUENTIAL_PATTERNS:
            if re.search(pattern, norm_name):
                return ApprovalEvaluation(
                    requires_approval=True,
                    reason=f"{reason} ('{action_name}')",
                    risk_level=risk_level,
                )

        # 5. Tool category or permissions check
        category = str(metadata.get("category", "")).lower()
        if category in ("destructive", "consequential", "payment", "security"):
            return ApprovalEvaluation(
                requires_approval=True,
                reason=f"Action '{action_name}' belongs to consequential category '{category}'.",
                risk_level=ApprovalRiskLevel.HIGH,
            )

        # 6. If explicitly safe prefix and didn't match consequential
        if is_safe_prefix:
            return ApprovalEvaluation(
                requires_approval=False,
                reason=f"Action '{action_name}' is classified as low-impact or read-only.",
                risk_level=ApprovalRiskLevel.LOW,
            )

        # 7. Fallback to default policy setting
        return ApprovalEvaluation(
            requires_approval=self._default_require_approval,
            reason=f"Action '{action_name}' evaluated under default policy.",
            risk_level=ApprovalRiskLevel.NORMAL,
        )
