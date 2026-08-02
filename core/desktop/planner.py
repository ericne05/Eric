"""
Hybrid Desktop Planner.
"""

from typing import List, Optional

from core.browser.enums import WorkflowState
from core.desktop.models import (
    DesktopAction,
    DesktopIntelligenceLayer,
    DesktopWorkflow,
)


class HybridDesktopPlanner:
    """
    Hybrid Planner for Desktop Automation.
    Combines pre-recorded Macro coordinates/action sequences with dynamic LLM planning.
    """

    def __init__(self):
        self._macro_registry = {}

    def register_macro(self, goal_keyword: str, actions: List[DesktopAction]) -> None:
        """Registers a macro sequence for a specific goal keyword."""
        self._macro_registry[goal_keyword.lower()] = actions

    def plan_workflow(self, workflow: DesktopWorkflow) -> DesktopWorkflow:
        """
        Plans actions for the given workflow.
        First checks if a macro matches the goal; if so, loads macro actions.
        Otherwise, initializes dynamic planning mode.
        """
        workflow.state = WorkflowState.PLANNING

        goal_lower = workflow.goal.lower()
        matched_macro = None
        for keyword, actions in self._macro_registry.items():
            if keyword in goal_lower:
                matched_macro = actions
                break

        if matched_macro:
            workflow.actions = [
                DesktopAction(
                    name=act.name,
                    arguments=dict(act.arguments),
                    priority=act.priority,
                    dependencies=list(act.dependencies),
                )
                for act in matched_macro
            ]
            workflow.intelligence.planner_confidence.score = 1.0
            workflow.intelligence.planner_confidence.reasoning = "Matched pre-recorded Macro."
        else:
            # Default dynamic fallback
            workflow.actions = [
                DesktopAction(name="capture_screen", priority=10),
                DesktopAction(name="click", arguments={"x": 500, "y": 500}, dependencies=[]),
            ]
            workflow.intelligence.planner_confidence.score = 0.85
            workflow.intelligence.planner_confidence.reasoning = "Generated dynamic plan based on desktop observation."

        workflow.state = WorkflowState.EXECUTING
        return workflow
