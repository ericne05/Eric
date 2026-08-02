"""
Cognitive Coordination Layer Enums (Sprint 16).
"""

from enum import Enum


class MessageType(str, Enum):
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    SUGGESTION = "suggestion"
    QUESTION = "question"
    RECOVERY_PROPOSAL = "recovery_proposal"


class PolicyType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PRIORITY = "priority"
    CONSENSUS = "consensus"


class AgentRole(str, Enum):
    PLANNER = "planner"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"
    RECOVERY = "recovery"
    COORDINATOR = "coordinator"


class CognitionState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    DISPATCHING = "dispatching"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
