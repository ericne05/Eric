"""
Goal Dashboard Widget Component.
Displays progress bar (0% -> 100%) and current goal status.
"""

from typing import Dict, Any


class GoalDashboardWidget:
    """
    Goal Progress Dashboard Widget.
    """

    def __init__(self):
        self.progress_percentage: float = 0.0
        self.current_step: int = 0
        self.total_steps: int = 0
        self.status_text: str = "Idle"

    def update_progress(self, percentage: float, current_step: int, total_steps: int, status_text: str = "") -> None:
        self.progress_percentage = percentage
        self.current_step = current_step
        self.total_steps = total_steps
        if status_text:
            self.status_text = status_text

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return {
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "status_text": self.status_text,
        }
