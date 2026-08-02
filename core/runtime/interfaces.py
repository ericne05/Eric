"""
Unified Runtime Interface (IRuntime).

All Runtimes in Eric (Browser, Desktop, Vision, Voice) MUST implement this interface.
This ensures a consistent Observe → Plan → Execute → Recover lifecycle
across every subsystem.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.browser.enums import WorkflowState


class IRuntimeCapability(ABC):
    """Interface for querying what a Runtime can do."""

    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """Returns a dict of capability_name -> is_supported."""
        pass

    @abstractmethod
    def supports(self, capability: str) -> bool:
        """Returns True if the runtime supports the given capability."""
        pass

    @abstractmethod
    def get_capability_list(self) -> List[str]:
        """Returns only the list of supported capability names."""
        pass


class IRuntime(ABC):
    """
    Unified Runtime Interface.

    Every Runtime in Eric (Browser, Desktop, Vision, Voice) implements
    the same lifecycle: observe → plan → execute → recover → shutdown.

    This enables the Orchestrator/Planner to treat all Runtimes uniformly
    and negotiate capabilities before choosing which Runtime to dispatch to.
    """

    @abstractmethod
    async def start(self) -> None:
        """Boot up the runtime and prepare resources."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shut down the runtime and release resources."""
        pass

    @abstractmethod
    async def observe(self) -> Any:
        """
        Collect an observation of the current environment state.
        Returns a Runtime-specific Observation object.
        """
        pass

    @abstractmethod
    async def plan(self, goal: str, observation: Any) -> Any:
        """
        Given a goal and an observation, produce a plan (list of actions).
        Returns a Runtime-specific Workflow or action list.
        """
        pass

    @abstractmethod
    async def execute(self, plan: Any) -> Any:
        """
        Execute a plan produced by the plan() method.
        Returns a Runtime-specific result.
        """
        pass

    @abstractmethod
    async def recover(self, error: Exception, context: Any) -> WorkflowState:
        """
        Handle a failure during execution.
        Returns the new WorkflowState after recovery attempt.
        """
        pass

    @abstractmethod
    def get_runtime_capabilities(self) -> IRuntimeCapability:
        """Returns the capability negotiation object for this runtime."""
        pass

    @abstractmethod
    def get_health(self) -> Dict[str, Any]:
        """Returns a health status dict for this runtime."""
        pass
