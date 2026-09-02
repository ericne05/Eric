"""
Agent Runtime Models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from core.agents.enums import StepType, TaskState


class CancellationToken:
    """
    Object to signal cancellation to the Task, LLM Service, and Tool Providers.
    """
    def __init__(self):
        self.is_cancelled: bool = False
        self.reason: str | None = None

    def cancel(self, reason: str = "User cancelled") -> None:
        self.is_cancelled = True
        self.reason = reason


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Step:
    """
    An individual step in a Task's execution timeline.
    """
    type: StepType
    content: str
    timestamp: datetime = field(default_factory=_now_utc)


@dataclass
class Task:
    """
    Represents a task to be executed by an Agent.
    """
    id: str
    goal: str
    agent_name: str
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    state: TaskState = TaskState.PENDING
    steps: list[Step] = field(default_factory=list)
    
    # Scheduler metadata
    priority: int = 0
    deadline: datetime | None = None
    retry_count: int = 0
    timeout_seconds: int = 300
    
    # Context data passed to the Agent
    context_data: dict[str, Any] = field(default_factory=dict)
    
    # Optional assigned agent
    agent_name: str | None = None
    
    # Result of the task
    result: Any | None = None
