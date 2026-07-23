"""
Agent Runtime Enums.
"""

from enum import Enum


class TaskState(str, Enum):
    """
    Lifecycle states of a Task.
    """
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """
    Types of steps in an Agent's ReAct loop.
    """
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
