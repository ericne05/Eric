"""
Goal Subsystem Package (Sprint 14 Product-Grade v1.0).
"""

from core.goals.adapters.mock_goal_adapter import MockGoalAdapter
from core.goals.decomposition import GoalDecomposer
from core.goals.enums import GoalPriority, GoalState, GoalType, RelationType, StepPolicy
from core.goals.estimator import GoalCostEstimator
from core.goals.interfaces import (
    ICostEstimator,
    IGoalManager,
    IGoalPlanner,
    IGoalValidator,
    IProgressTracker,
    IReplanner,
)
from core.goals.managers.execution_context import ContextSnapshot, ExecutionContext
from core.goals.managers.goal_manager import GoalManager
from core.goals.managers.progress_tracker import ProgressTracker
from core.goals.managers.recovery import GoalRecoveryManager
from core.goals.models import (
    CapabilityRequirement,
    DAGRelation,
    ExecutionPlan,
    ExecutionStep,
    Goal,
    GoalArtifact,
    GoalCostEstimate,
    GoalDependencyGraph,
    GoalMemoryReference,
    GoalPolicy,
    GoalProgress,
    GoalResult,
    GoalSpecification,
    SubGoal,
    SuccessCriterion,
)
from core.goals.orchestrator import GoalOrchestrator
from core.goals.planner import AutonomousGoalPlanner, DynamicReplanner
from core.goals.validators import GoalValidator

__all__ = [
    "GoalState",
    "GoalPriority",
    "GoalType",
    "RelationType",
    "StepPolicy",
    "SuccessCriterion",
    "GoalSpecification",
    "CapabilityRequirement",
    "GoalPolicy",
    "GoalArtifact",
    "SubGoal",
    "DAGRelation",
    "GoalDependencyGraph",
    "ExecutionStep",
    "ExecutionPlan",
    "GoalCostEstimate",
    "GoalProgress",
    "GoalResult",
    "GoalMemoryReference",
    "Goal",
    "ICostEstimator",
    "IReplanner",
    "IGoalPlanner",
    "IProgressTracker",
    "IGoalValidator",
    "IGoalManager",
    "GoalCostEstimator",
    "GoalDecomposer",
    "GoalValidator",
    "DynamicReplanner",
    "AutonomousGoalPlanner",
    "GoalOrchestrator",
    "ProgressTracker",
    "ContextSnapshot",
    "ExecutionContext",
    "GoalRecoveryManager",
    "GoalManager",
    "MockGoalAdapter",
]
