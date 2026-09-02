"""
Telemetry Dashboard for Eric (Sprint 14 Goal Integration).

Collects metrics from EventBus and provides a real-time snapshot
of system health: Queue Length, Planner Confidence, Runtime Health,
Recovery Count, Action Duration, Success Rate, AND Goal Metrics.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.events.event import Event
from core.events.event_bus import EventBus


@dataclass
class ActionMetric:
    """Stores duration and result of a single action execution."""
    action_name: str
    success: bool
    duration_ms: int = 0
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    runtime_name: str = ""
    confidence: float = 1.0


@dataclass
class DashboardSnapshot:
    """A point-in-time snapshot of system telemetry."""
    timestamp: datetime.datetime
    queue_length: int = 0
    planner_confidence: float = 1.0
    runtime_health: Dict[str, str] = field(default_factory=dict)
    recovery_count: int = 0
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    avg_duration_ms: float = 0.0
    success_rate: float = 1.0
    # Goal Metrics
    total_goals: int = 0
    active_goals: int = 0
    completed_goals: int = 0
    failed_goals: int = 0


class TelemetryDashboard:
    """
    Real-time Telemetry Dashboard.
    Subscribes to EventBus events for Runtimes and Goals.
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._action_metrics: List[ActionMetric] = []
        self._recovery_count: int = 0
        self._queue_length: int = 0
        self._planner_confidence: float = 1.0
        self._runtime_health: Dict[str, str] = {}

        # Goal metrics
        self._total_goals: int = 0
        self._active_goals: int = 0
        self._completed_goals: int = 0
        self._failed_goals: int = 0

        # Subscriptions
        self._event_bus.subscribe("desktop.action.completed", self._on_action_completed)
        self._event_bus.subscribe("desktop.action.failed", self._on_action_failed)
        self._event_bus.subscribe("desktop.action.started", self._on_action_started)
        self._event_bus.subscribe("desktop.state.changed", self._on_state_changed)
        self._event_bus.subscribe("desktop.emergency_stop", self._on_emergency_stop)
        self._event_bus.subscribe("browser.action.completed", self._on_action_completed)
        self._event_bus.subscribe("browser.action.failed", self._on_action_failed)

        # Goal subscriptions
        self._event_bus.subscribe("goal.created", self._on_goal_created)
        self._event_bus.subscribe("goal.started", self._on_goal_started)
        self._event_bus.subscribe("goal.completed", self._on_goal_completed)
        self._event_bus.subscribe("goal.failed", self._on_goal_failed)
        self._event_bus.subscribe("goal.recovered", self._on_goal_recovered)

    def _on_goal_created(self, event: Event) -> None:
        self._total_goals += 1

    def _on_goal_started(self, event: Event) -> None:
        self._active_goals += 1

    def _on_goal_completed(self, event: Event) -> None:
        self._active_goals = max(0, self._active_goals - 1)
        self._completed_goals += 1

    def _on_goal_failed(self, event: Event) -> None:
        self._active_goals = max(0, self._active_goals - 1)
        self._failed_goals += 1

    def _on_goal_recovered(self, event: Event) -> None:
        self._recovery_count += 1

    def _on_action_started(self, event: Event) -> None:
        self._queue_length += 1

    def _on_action_completed(self, event: Event) -> None:
        self._queue_length = max(0, self._queue_length - 1)
        payload = event.payload or {}
        result = payload.get("result")
        duration = 0
        confidence = self._planner_confidence

        if result and hasattr(result, "elapsed_ms"):
            duration = result.elapsed_ms
        if result and hasattr(result, "confidence_score"):
            confidence = result.confidence_score

        self._action_metrics.append(
            ActionMetric(
                action_name=payload.get("action", "unknown"),
                success=True,
                duration_ms=duration,
                runtime_name=event.source,
                confidence=confidence,
            )
        )

    def _on_action_failed(self, event: Event) -> None:
        self._queue_length = max(0, self._queue_length - 1)
        self._recovery_count += 1
        payload = event.payload or {}
        self._action_metrics.append(
            ActionMetric(
                action_name=payload.get("action", "unknown"),
                success=False,
                runtime_name=event.source,
            )
        )

    def _on_state_changed(self, event: Event) -> None:
        payload = event.payload or {}
        state = payload.get("state", "unknown")
        self._runtime_health[event.source] = state

    def _on_emergency_stop(self, event: Event) -> None:
        self._recovery_count += 1

    def update_planner_confidence(self, score: float) -> None:
        self._planner_confidence = score

    def update_runtime_health(self, runtime_name: str, state: str) -> None:
        self._runtime_health[runtime_name] = state

    def snapshot(self) -> DashboardSnapshot:
        total = len(self._action_metrics)
        successful = sum(1 for m in self._action_metrics if m.success)
        failed = total - successful
        durations = [m.duration_ms for m in self._action_metrics if m.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        success_rate = (successful / total) if total > 0 else 1.0

        return DashboardSnapshot(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            queue_length=self._queue_length,
            planner_confidence=self._planner_confidence,
            runtime_health=dict(self._runtime_health),
            recovery_count=self._recovery_count,
            total_actions=total,
            successful_actions=successful,
            failed_actions=failed,
            avg_duration_ms=avg_duration,
            success_rate=success_rate,
            total_goals=self._total_goals,
            active_goals=self._active_goals,
            completed_goals=self._completed_goals,
            failed_goals=self._failed_goals,
        )

    def reset(self) -> None:
        self._action_metrics.clear()
        self._recovery_count = 0
        self._queue_length = 0
        self._planner_confidence = 1.0
        self._runtime_health.clear()
        self._total_goals = 0
        self._active_goals = 0
        self._completed_goals = 0
        self._failed_goals = 0
