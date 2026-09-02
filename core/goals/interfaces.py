"""
Goal Manager Interfaces (Sprint 14 Product-Grade).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.goals.models import (
    ExecutionPlan,
    ExecutionStep,
    Goal,
    GoalCostEstimate,
    GoalProgress,
    GoalResult,
    GoalSpecification,
)


class ICostEstimator(ABC):
    """Interface for Pre-execution cost estimation."""

    @abstractmethod
    def estimate_cost(self, spec: GoalSpecification, plan: ExecutionPlan) -> GoalCostEstimate:
        pass


class IReplanner(ABC):
    """Interface for independent replanning strategy when environment changes or errors occur."""

    @abstractmethod
    def replan(self, goal: Goal, failed_step: ExecutionStep, error_msg: str) -> ExecutionPlan:
        pass


class IGoalPlanner(ABC):
    """Interface for Goal decomposition and ExecutionPlan building."""

    @abstractmethod
    def decompose(self, spec: GoalSpecification) -> Goal:
        pass

    @abstractmethod
    def build_plan(self, goal: Goal) -> ExecutionPlan:
        pass


class IProgressTracker(ABC):
    """Interface for tracking real-time progress of Goal execution."""

    @abstractmethod
    def update_progress(self, goal_id: str, step_index: int, total_steps: int, current_runtime: str) -> GoalProgress:
        pass

    @abstractmethod
    def get_progress(self, goal_id: str) -> Optional[GoalProgress]:
        pass


class IGoalValidator(ABC):
    """Interface for validating steps and final completion criteria."""

    @abstractmethod
    def validate_step(self, step: ExecutionStep, result_data: Any) -> bool:
        pass

    @abstractmethod
    def validate_completion(self, goal: Goal) -> bool:
        pass


class IGoalManager(ABC):
    """
    Main Goal Manager Interface.
    Orchestrates Goal lifecycle (Create -> Plan -> Estimate -> Run -> Pause -> Resume -> Complete/Fail).
    Does NOT execute actions directly.
    """

    @abstractmethod
    async def create_goal(self, description: str, **kwargs) -> Goal:
        pass

    @abstractmethod
    async def start_goal(self, goal_id: str) -> GoalResult:
        pass

    @abstractmethod
    async def pause_goal(self, goal_id: str) -> bool:
        pass

    @abstractmethod
    async def resume_goal(self, goal_id: str) -> GoalResult:
        pass

    @abstractmethod
    async def cancel_goal(self, goal_id: str) -> bool:
        pass

    @abstractmethod
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        pass
