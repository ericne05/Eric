"""
Runtime Models for Eric Desktop Companion.

Defines transport-agnostic, serializable models for the Eric Runtime Host:
- RuntimeStatus: Lifecycle state machine for the companion runtime
- RuntimeErrorInfo: Safe structured error model
- RuntimeEvent: Structured client-facing lifecycle/operational event
- RuntimeSnapshot: Serializable snapshot of runtime state for clients
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional


class RuntimeStatus(str, Enum):
    """
    Lifecycle states for the Eric Runtime Host.

    Represents companion-level host lifecycle independently of internal Kernel state.
    Transition diagram:
        CREATED -> STARTING -> READY -> BUSY -> READY -> STOPPING -> STOPPED
        (Any active state) -> ERROR
    """
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True)
class RuntimeErrorInfo:
    """
    Safe structured error model that can cross the client/runtime boundary.

    Internal stack traces and secrets remain in logs; clients receive
    safe structured diagnostic information.
    """
    code: str
    message: str
    recoverable: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to a JSON-serializable dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeErrorInfo":
        """Reconstruct from dictionary."""
        ts = data.get("timestamp")
        parsed_ts = datetime.fromisoformat(ts) if isinstance(ts, str) else datetime.now(timezone.utc)
        return cls(
            code=data.get("code", "UNKNOWN_ERROR"),
            message=data.get("message", "An unknown error occurred"),
            recoverable=bool(data.get("recoverable", False)),
            timestamp=parsed_ts,
        )


@dataclass(frozen=True)
class RuntimeEvent:
    """
    Structured runtime event transmitted to clients.

    Payloads MUST NOT contain raw secrets, API keys, or unredacted environment data.
    """
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to a JSON-serializable dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeEvent":
        """Reconstruct from dictionary."""
        ts = data.get("timestamp")
        parsed_ts = datetime.fromisoformat(ts) if isinstance(ts, str) else datetime.now(timezone.utc)
        return cls(
            event_type=data.get("event_type", "unknown"),
            timestamp=parsed_ts,
            payload=data.get("payload", {}),
        )


@dataclass(frozen=True)
class RuntimeSnapshot:
    """
    Serializable snapshot of the Eric Runtime state.

    Contains no live Python service objects, ensuring compatibility with
    in-process calls, local IPC, and remote transports.
    """
    status: RuntimeStatus
    started_at: Optional[datetime] = None
    active_goal_id: Optional[str] = None
    last_error: Optional[RuntimeErrorInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to a JSON-serializable dictionary."""
        return {
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "active_goal_id": self.active_goal_id,
            "last_error": self.last_error.to_dict() if self.last_error else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeSnapshot":
        """Reconstruct from dictionary."""
        raw_status = data.get("status", RuntimeStatus.CREATED.value)
        status = RuntimeStatus(raw_status) if raw_status in RuntimeStatus._value2member_map_ else RuntimeStatus.CREATED

        started_at = None
        if data.get("started_at"):
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except (ValueError, TypeError):
                pass

        last_error = None
        if data.get("last_error"):
            last_error = RuntimeErrorInfo.from_dict(data["last_error"])

        return cls(
            status=status,
            started_at=started_at,
            active_goal_id=data.get("active_goal_id"),
            last_error=last_error,
        )


@dataclass(frozen=True)
class GoalHandle:
    """
    Client-safe handle representing an initiated or queued goal.

    Contains no live domain/engine objects.
    """
    goal_id: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalHandle":
        return cls(
            goal_id=data.get("goal_id", ""),
            status=data.get("status", "unknown"),
        )


@dataclass(frozen=True)
class GoalSnapshot:
    """
    Client-safe snapshot of a goal's current progress and execution state.

    Contains no live domain/engine objects; completely JSON-serializable.
    """
    goal_id: str
    description: str
    status: str
    progress: float = 0.0
    current_step: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalSnapshot":
        return cls(
            goal_id=data.get("goal_id", ""),
            description=data.get("description", ""),
            status=data.get("status", "unknown"),
            progress=float(data.get("progress", 0.0)),
            current_step=data.get("current_step"),
            total_steps=int(data.get("total_steps", 0)),
            completed_steps=int(data.get("completed_steps", 0)),
            error=data.get("error"),
        )


@dataclass(frozen=True)
class GoalProgressRecord:
    """
    Transport-safe progress update for telemetry and UI timelines.

    Payloads never contain private chain-of-thought or raw internal reasoning.
    """
    goal_id: str
    state: str
    current_step: Optional[str] = None
    completed_steps: int = 0
    total_steps: int = 0
    percentage: float = 0.0
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "state": self.state,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "percentage": self.percentage,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalProgressRecord":
        return cls(
            goal_id=data.get("goal_id", ""),
            state=data.get("state", "unknown"),
            current_step=data.get("current_step"),
            completed_steps=int(data.get("completed_steps", 0)),
            total_steps=int(data.get("total_steps", 0)),
            percentage=float(data.get("percentage", 0.0)),
            message=data.get("message"),
        )
