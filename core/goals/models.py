"""
Goal Manager Data Models (Sprint 14 Product-Grade v1.0).
Includes SuccessCriterion, CapabilityRequirement, GoalPolicy, and GoalArtifact.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import uuid

from core.goals.enums import (
    GoalPriority,
    GoalState,
    GoalType,
    RelationType,
    StepPolicy,
)


@dataclass
class SuccessCriterion:
    """Explicit criterion used to validate goal or step completion."""
    criterion_type: str  # 'file_exists', 'min_size', 'extension_match', 'text_contains', 'condition_expr'
    target: str = ""
    expected_value: Any = None


@dataclass
class GoalSpecification:
    """
    Goal Specification — Defines WHAT the user wants to achieve.
    Strictly separated from the ExecutionPlan (HOW to achieve it).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    intent: str = ""
    description: str = ""
    goal_type: GoalType = GoalType.MIXED
    priority: GoalPriority = GoalPriority.NORMAL
    success_criteria: List[SuccessCriterion] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    expected_result: Any = None
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityRequirement:
    """Layered capability requirement allowing graceful runtime fallbacks."""
    required: List[str] = field(default_factory=list)   # Hard requirement (e.g. ['desktop'])
    preferred: List[str] = field(default_factory=list)  # Preferred runtime (e.g. ['vision'])
    optional: List[str] = field(default_factory=list)   # Optional runtime (e.g. ['browser'])


@dataclass
class GoalPolicy:
    """Policy rules governing Planner & Orchestrator behavior for a Goal."""
    allow_parallel: bool = True
    allow_retry: bool = True
    allow_user_confirmation: bool = False
    allow_replanning: bool = True
    allow_partial_success: bool = False


@dataclass
class GoalArtifact:
    """
    Goal Artifact — Structured output produced after Goal completion.
    Serves as persistent reference for future goals and Knowledge Graph (Sprint 15).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    title: str = ""
    summary: str = ""
    files_generated: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    telemetry_snapshot: Dict[str, Any] = field(default_factory=dict)
    memory_reference_id: Optional[str] = None
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


@dataclass
class SubGoal:
    """A sub-goal node within a Goal Dependency Graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    capability_requirement: CapabilityRequirement = field(default_factory=CapabilityRequirement)
    status: str = "pending"  # pending, running, completed, failed, skipped
    result_data: Any = None


@dataclass
class DAGRelation:
    """A directed edge between two SubGoals in a Goal DAG."""
    source_subgoal_id: str
    target_subgoal_id: str
    relation_type: RelationType = RelationType.REQUIRED
    condition_expr: Optional[str] = None


@dataclass
class GoalDependencyGraph:
    """Multi-relation DAG storing SubGoals and their relationships."""
    subgoals: Dict[str, SubGoal] = field(default_factory=dict)
    relations: List[DAGRelation] = field(default_factory=list)

    def add_subgoal(self, subgoal: SubGoal) -> None:
        self.subgoals[subgoal.id] = subgoal

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType = RelationType.REQUIRED,
        condition_expr: Optional[str] = None,
    ) -> None:
        self.relations.append(
            DAGRelation(
                source_subgoal_id=source_id,
                target_subgoal_id=target_id,
                relation_type=relation_type,
                condition_expr=condition_expr,
            )
        )

    def get_prerequisites(self, subgoal_id: str) -> List[Tuple[SubGoal, RelationType]]:
        prereqs = []
        for rel in self.relations:
            if rel.target_subgoal_id == subgoal_id and rel.source_subgoal_id in self.subgoals:
                prereqs.append((self.subgoals[rel.source_subgoal_id], rel.relation_type))
        return prereqs


@dataclass
class ExecutionStep:
    """A single concrete step inside an ExecutionPlan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subgoal_id: str = ""
    action_name: str = ""
    capability_requirement: CapabilityRequirement = field(default_factory=CapabilityRequirement)
    arguments: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    policy: StepPolicy = StepPolicy.RECOVER
    estimated_duration_sec: float = 1.0


@dataclass
class ExecutionPlan:
    """Concrete execution plan mapping steps to capabilities."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    steps: List[ExecutionStep] = field(default_factory=list)
    version: int = 1


@dataclass
class GoalCostEstimate:
    """Pre-execution cost estimation."""
    estimated_seconds: float = 0.0
    estimated_tokens: int = 0
    estimated_steps: int = 0
    estimated_confidence: float = 1.0


@dataclass
class GoalProgress:
    """Realtime progress metrics for Telemetry and UI."""
    goal_id: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    percentage: float = 0.0
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    current_runtime: str = "none"
    recovery_count: int = 0
    planner_confidence: float = 1.0


@dataclass
class GoalResult:
    """Final output result of a Goal execution."""
    success: bool
    goal_id: str
    output_data: Any = None
    error: Optional[str] = None
    summary: str = ""
    artifact_id: Optional[str] = None


@dataclass
class GoalMemoryReference:
    """Summary reference to be persisted into Vector Memory / Knowledge Graph."""
    goal_id: str
    description: str
    success: bool
    summary: str
    artifact_id: Optional[str] = None
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


@dataclass
class Goal:
    """
    Root Goal Container.
    Holds Specification, Policy, Dependency Graph, Execution Plan, Cost Estimate, Progress, and Artifact.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spec: GoalSpecification = field(default_factory=GoalSpecification)
    policy: GoalPolicy = field(default_factory=GoalPolicy)
    graph: GoalDependencyGraph = field(default_factory=GoalDependencyGraph)
    plan: ExecutionPlan = field(default_factory=ExecutionPlan)
    cost_estimate: GoalCostEstimate = field(default_factory=GoalCostEstimate)
    progress: GoalProgress = field(default_factory=GoalProgress)
    state: GoalState = GoalState.CREATED
    result: Optional[GoalResult] = None
    artifact: Optional[GoalArtifact] = None
