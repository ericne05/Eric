"""
Policy Implementation.
"""

from typing import Any

from core.security.enums import PolicyDecision
from core.security.interfaces import IPolicyEngine, PolicyResult


class AllowAllPolicy(IPolicyEngine):
    """
    A basic policy that allows all actions.
    """
    def evaluate_action(self, action: Any, context: Any = None) -> PolicyResult:
        # In a real engine, we would inspect the action and return appropriate decisions
        return PolicyResult(decision=PolicyDecision.ALLOW, reason="Allow all policy is active.")
