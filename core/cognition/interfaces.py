"""
Cognitive Coordination Layer Interfaces (Sprint 16).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from core.cognition.enums import AgentRole
from core.cognition.models import AgentMessage, CognitionResult, SharedCognitiveContext


class ICognitiveAgent(ABC):
    """Interface for all Cognitive Agents (Planning, Execution, Knowledge, Recovery)."""

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        pass

    @abstractmethod
    async def process_message(self, message: AgentMessage, context: SharedCognitiveContext) -> CognitionResult:
        pass


class ICoordinatorPolicy(ABC):
    """Interface for Cognitive Coordinator Policy (Sequential, Parallel, Priority, Consensus)."""

    @abstractmethod
    def select_execution_order(self, agents: List[ICognitiveAgent]) -> List[ICognitiveAgent]:
        pass


class ICognitiveCoordinator(ABC):
    """Main Cognitive Coordinator interface."""

    @abstractmethod
    async def run_cognition_loop(self, context: SharedCognitiveContext) -> CognitionResult:
        pass
