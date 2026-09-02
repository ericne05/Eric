"""
Security Interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.security.enums import PolicyDecision


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str | None = None


class IPolicyEngine(ABC):
    """
    Engine to evaluate actions against security policies.
    """
    @abstractmethod
    def evaluate_action(self, action: Any, context: Any = None) -> PolicyResult:
        """
        Evaluate if an action is allowed.
        action can be a Tool Call, a Command, etc.
        """
        pass
