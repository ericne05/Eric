"""
Real-time Goal Progress Tracker.
"""

from typing import Dict, Optional

from core.events.event import Event
from core.events.event_bus import EventBus
from core.goals.interfaces import IProgressTracker
from core.goals.models import GoalProgress


class ProgressTracker(IProgressTracker):
    """
    Tracks realtime Goal progress (% completed, step index, remaining time).
    Publishes goal.progress.updated events via EventBus.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._progress_map: Dict[str, GoalProgress] = {}

    def update_progress(self, goal_id: str, step_index: int, total_steps: int, current_runtime: str) -> GoalProgress:
        pct = (step_index / total_steps * 100.0) if total_steps > 0 else 0.0
        remaining_sec = float(max(0, total_steps - step_index) * 2)

        progress = GoalProgress(
            goal_id=goal_id,
            current_step_index=step_index,
            total_steps=total_steps,
            percentage=round(pct, 1),
            estimated_remaining_seconds=remaining_sec,
            current_runtime=current_runtime,
        )
        self._progress_map[goal_id] = progress

        if self._event_bus:
            self._event_bus.publish_sync(
                Event(
                    name="goal.progress.updated",
                    source="progress_tracker",
                    payload={"goal_id": goal_id, "percentage": pct, "step_index": step_index, "current_runtime": current_runtime},
                )
            )
        return progress

    def get_progress(self, goal_id: str) -> Optional[GoalProgress]:
        return self._progress_map.get(goal_id)
