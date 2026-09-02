"""
Execution Context & Full State Snapshot Persistence.
Supports Pause, Resume, and Interruption Recovery for Goals.
"""

from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, Optional

from core.goals.models import Goal, GoalState


@dataclass
class ContextSnapshot:
    """Full snapshot of system state at a specific step in Goal execution."""
    goal_id: str
    step_index: int
    browser_state: Dict[str, Any] = field(default_factory=dict)
    desktop_state: Dict[str, Any] = field(default_factory=dict)
    vision_state: Dict[str, Any] = field(default_factory=dict)
    memory_references: Dict[str, Any] = field(default_factory=dict)
    current_runtime: str = "none"
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class ExecutionContext:
    """
    Holds persistent state for running Goals.
    Supports capturing snapshots for Pause / Resume.
    """

    def __init__(self):
        self._snapshots: Dict[str, ContextSnapshot] = {}

    def capture_snapshot(self, goal: Goal, step_index: int, runtime_name: str = "none") -> ContextSnapshot:
        snapshot = ContextSnapshot(
            goal_id=goal.id,
            step_index=step_index,
            current_runtime=runtime_name,
            browser_state={"state": "active"},
            desktop_state={"state": "active"},
            vision_state={"state": "active"},
        )
        self._snapshots[goal.id] = snapshot
        return snapshot

    def get_snapshot(self, goal_id: str) -> Optional[ContextSnapshot]:
        return self._snapshots.get(goal_id)

    def restore_goal_state(self, goal: Goal) -> int:
        """Restores goal state from snapshot, returning the step_index to resume from."""
        snapshot = self._snapshots.get(goal.id)
        if snapshot:
            goal.state = GoalState.RUNNING
            return snapshot.step_index
        return 0
