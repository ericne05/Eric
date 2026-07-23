"""
Agent Runtime Interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.agents.models import Task
from core.config.schemas import SystemConfig
from core.events.event_bus import EventBus
from core.logger.interface import ILogger
from core.memory.interfaces import IMemoryService
from core.tools.interfaces import IToolExecutor


@dataclass(frozen=True)
class ExecutionContext:
    """
    The context provided to an Agent during Task execution.
    This encapsulates common subsystems and avoids injecting the full DI Container.
    """
    task: Task
    logger: ILogger
    event_bus: EventBus
    config: SystemConfig
    memory: IMemoryService
    tool_executor: IToolExecutor


class IAgent(ABC):
    """
    Contract for all Agents. Defines the ReAct loop phases.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the Agent."""
        pass

    @abstractmethod
    def plan(self, context: ExecutionContext) -> str | None:
        """
        Thought phase: Think about the next step.
        Returns the thought as a string, or None if the task is finished.
        """
        pass

    @abstractmethod
    def act(self, context: ExecutionContext, thought: str) -> Any:
        """
        Action phase: Perform an action based on the thought.
        Returns the action definition or action object.
        """
        pass

    @abstractmethod
    def observe(self, context: ExecutionContext, action_result: Any) -> str:
        """
        Observation phase: Analyze the result of the action.
        Returns the observation as a string.
        """
        pass


class IAgentRegistry(ABC):
    """
    Registry for managing available Agents.
    """
    @abstractmethod
    def register(self, agent: IAgent) -> None:
        pass

    @abstractmethod
    def get_agent(self, name: str) -> IAgent | None:
        pass

    @abstractmethod
    def get_all(self) -> list[IAgent]:
        pass


class IAgentRuntime(ABC):
    """
    The orchestrator that executes Tasks using Agents.
    """
    @abstractmethod
    def submit_task(self, task: Task) -> None:
        """Submit a task for execution."""
        pass

    @abstractmethod
    def cancel_task(self, task_id: str) -> None:
        """Cancel a running or pending task."""
        pass

    @abstractmethod
    def process_queue(self) -> None:
        """Process pending tasks in the queue."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by ID."""
        pass
