"""
Desktop Recovery Manager.
"""

from typing import Optional

from core.browser.enums import WorkflowState
from core.desktop.models import DesktopAction, DesktopWorkflow


class DesktopRecoveryManager:
    """
    Handles error recovery for Desktop workflows when actions fail.
    Implements backoff retries, alternative fallback actions, and state transitions to RECOVERING.
    """

    def __init__(self, max_recovery_attempts: int = 3):
        self._max_recovery_attempts = max_recovery_attempts

    def handle_action_failure(self, workflow: DesktopWorkflow, failed_action: DesktopAction, error_message: str) -> WorkflowState:
        """
        Determines the next WorkflowState when an action fails.
        If retry count < max_retries, it switches to RECOVERING to attempt backoff or fallback.
        Otherwise, transitions to FAILED.
        """
        failed_action.status = "failed"
        failed_action.retry_count += 1

        if failed_action.retry_count <= failed_action.max_retries:
            workflow.state = WorkflowState.RECOVERING
            workflow.intelligence.planner_confidence.score *= 0.8  # Reduce confidence score
            workflow.intelligence.planner_confidence.reasoning = (
                f"Action '{failed_action.name}' failed with error: {error_message}. Attempting recovery retry {failed_action.retry_count}."
            )
            if workflow.intelligence.planner_confidence.score < 0.3:
                workflow.intelligence.planner_confidence.needs_human_help = True
            return WorkflowState.RECOVERING
        else:
            workflow.state = WorkflowState.FAILED
            workflow.intelligence.planner_confidence.score = 0.0
            workflow.intelligence.planner_confidence.reasoning = f"Action '{failed_action.name}' exceeded maximum retries."
            return WorkflowState.FAILED

    def reset_for_retry(self, failed_action: DesktopAction) -> DesktopAction:
        """Resets action status back to pending for retry execution."""
        failed_action.status = "pending"
        return failed_action
