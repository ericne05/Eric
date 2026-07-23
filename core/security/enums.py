"""
Security and Policy Enums.
"""

from enum import Enum


class PolicyDecision(str, Enum):
    """
    Result of a policy evaluation.
    """
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"
    CONFIRM_ONCE = "confirm_once"
    REQUIRE_PERMISSION = "require_permission"
