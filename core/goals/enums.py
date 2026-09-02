"""
Goal Manager Enums.
"""

from enum import Enum


class GoalState(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    ESTIMATING = "estimating"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class GoalType(str, Enum):
    INFORMATION = "information"
    DESKTOP = "desktop"
    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    VISION = "vision"
    MIXED = "mixed"


class RelationType(str, Enum):
    """Dependency relations between SubGoals in a Goal DAG."""
    REQUIRED = "required"        # Must complete before target starts
    OPTIONAL = "optional"        # Failure does not break target or Goal
    PARALLEL = "parallel"        # Can run concurrently with target
    CONDITIONAL = "conditional"  # Runs only if prerequisite condition evaluates to True


class StepPolicy(str, Enum):
    CONTINUE = "continue"
    ABORT = "abort"
    RETRY = "retry"
    SKIP = "skip"
    ASK_USER = "ask_user"
    RECOVER = "recover"
