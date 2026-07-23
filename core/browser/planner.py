"""
Browser Planner Agent.
"""
from abc import ABC, abstractmethod
from typing import List

from core.browser.enums import WorkflowState
from core.browser.models import BrowserWorkflow, BrowserIntelligenceLayer, BrowserAction
from core.logger.interface import ILogger


class IBrowserPlanner(ABC):
    """Interface for the Browser Planner."""
    @abstractmethod
    def plan(self, workflow: BrowserWorkflow, intelligence: BrowserIntelligenceLayer) -> List[BrowserAction]:
        pass


class HybridBrowserPlanner(IBrowserPlanner):
    """
    A hybrid planner that uses macros for known sites and dynamic planning (LLM) for unknown ones.
    """
    def __init__(self, logger: ILogger):
        self._logger = logger
        
    def plan(self, workflow: BrowserWorkflow, intelligence: BrowserIntelligenceLayer) -> List[BrowserAction]:
        self._logger.info(f"[Planner] Analyzing intelligence layer for workflow {workflow.id}")
        workflow.state = WorkflowState.PLANNING
        
        obs = intelligence.observation
        
        # Macro check (Placeholder for actual DB lookup)
        if "github.com/login" in obs.url and "login" in workflow.goal.lower():
            self._logger.info("[Planner] Found matching macro for Github Login.")
            action1 = BrowserAction(name="type", arguments={"selector": "#login_field", "text": "username"})
            action2 = BrowserAction(name="type", arguments={"selector": "#password", "text": "password"}, dependencies=[action1.id])
            action3 = BrowserAction(name="click", arguments={"selector": "input[type='submit']"}, dependencies=[action2.id])
            
            actions = [action1, action2, action3]
            workflow.actions.extend(actions)
            return actions
            
        # Dynamic Planning (Placeholder for LLM call)
        self._logger.info("[Planner] No macro found. Generating dynamic plan based on observation.")
        # E.g. prompt LLM with observation.simplified_dom
        
        # Mock action
        action = BrowserAction(name="wait", arguments={"time": 1000})
        workflow.actions.append(action)
        
        return [action]
