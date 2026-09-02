"""
Cognitive Coordination Layer Models (Sprint 16).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from core.cognition.enums import AgentRole, MessageType
from core.goals.models import Goal, GoalArtifact, GoalSpecification
from core.knowledge.models import KnowledgeGraph


@dataclass
class AgentMessage:
    """Structured message passed between Cognitive Agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_role: AgentRole = AgentRole.COORDINATOR
    target_role: AgentRole = AgentRole.PLANNER
    message_type: MessageType = MessageType.TASK_REQUEST
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


@dataclass
class CognitiveTask:
    """A unit of task work dispatched between Cognitive Agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    subgoal_id: str = ""
    description: str = ""
    action_name: str = ""
    capability_requirement: Any = None
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitionResult:
    """Result emitted by a Cognitive Agent."""
    success: bool
    agent_role: AgentRole
    data: Any = None
    error: Optional[str] = None
    suggested_action: Optional[str] = None


@dataclass
class SharedCognitiveContext:
    """
    Shared Cognitive Context.
    Accessible by all Cognitive Agents (Planner, Execution, Knowledge, Recovery).
    Stores Goal, Plan, Knowledge Graph, Telemetry, and Execution History.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: Optional[Goal] = None
    knowledge_graph: Optional[KnowledgeGraph] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[GoalArtifact] = field(default_factory=list)
    telemetry_data: Dict[str, Any] = field(default_factory=dict)

    def record_history(self, event_type: str, details: Dict[str, Any]) -> None:
        self.history.append({
            "event": event_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "details": details,
        })
