"""
Unit Tests for Sprint 16 — Cognitive Coordination Layer.
"""

import pytest

from core.cognition import (
    AgentMessage,
    AgentRole,
    CognitiveCoordinator,
    CognitiveMessageBus,
    ExecutionAgent,
    KnowledgeAgent,
    MessageType,
    PlanningAgent,
    RecoveryAgent,
    SequentialPolicy,
    SharedCognitiveContext,
)
from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus
from core.goals import Goal, GoalSpecification, GoalType
from core.runtime.capability import CapabilityNegotiator
from core.vision import MockVisionAdapter


def test_cognitive_enums_and_messages():
    msg = AgentMessage(
        sender_role=AgentRole.COORDINATOR,
        target_role=AgentRole.PLANNER,
        message_type=MessageType.TASK_REQUEST,
        payload={"goal": "Download report"},
    )
    assert msg.sender_role == AgentRole.COORDINATOR
    assert msg.target_role == AgentRole.PLANNER
    assert msg.message_type == MessageType.TASK_REQUEST


def test_shared_cognitive_context_history():
    ctx = SharedCognitiveContext()
    ctx.record_history("plan_created", {"steps": 4})
    assert len(ctx.history) == 1
    assert ctx.history[0]["event"] == "plan_created"


@pytest.mark.asyncio
async def test_knowledge_agent_process():
    agent = KnowledgeAgent()
    spec = GoalSpecification(description="Download report", goal_type=GoalType.BROWSER)
    ctx = SharedCognitiveContext(goal=Goal(spec=spec))
    msg = AgentMessage(target_role=AgentRole.KNOWLEDGE)

    res = await agent.process_message(msg, ctx)
    assert res.success is True
    assert res.agent_role == AgentRole.KNOWLEDGE
    assert res.data["recommended_runtime"] is not None


@pytest.mark.asyncio
async def test_planning_agent_process():
    agent = PlanningAgent()
    spec = GoalSpecification(description="Execute desktop action")
    ctx = SharedCognitiveContext(goal=Goal(spec=spec))
    msg = AgentMessage(target_role=AgentRole.PLANNER)

    res = await agent.process_message(msg, ctx)
    assert res.success is True
    assert res.agent_role == AgentRole.PLANNER
    assert ctx.goal.plan is not None
    assert len(ctx.goal.plan.steps) > 0


@pytest.mark.asyncio
async def test_execution_agent_process():
    negotiator = CapabilityNegotiator()
    negotiator.register_runtime("desktop", MockDesktopAdapter())

    agent = ExecutionAgent(negotiator)
    spec = GoalSpecification(description="Execute desktop action")
    ctx = SharedCognitiveContext(goal=Goal(spec=spec))

    # Plan first
    planner = PlanningAgent()
    await planner.process_message(AgentMessage(target_role=AgentRole.PLANNER), ctx)

    # Execute
    msg = AgentMessage(target_role=AgentRole.EXECUTION)
    res = await agent.process_message(msg, ctx)
    assert res.success is True
    assert res.agent_role == AgentRole.EXECUTION


@pytest.mark.asyncio
async def test_recovery_agent_process():
    agent = RecoveryAgent()
    spec = GoalSpecification(description="Execute task")
    ctx = SharedCognitiveContext(goal=Goal(spec=spec))

    # Plan first
    planner = PlanningAgent()
    await planner.process_message(AgentMessage(target_role=AgentRole.PLANNER), ctx)

    failed_step = ctx.goal.plan.steps[0]
    msg = AgentMessage(
        target_role=AgentRole.RECOVERY,
        payload={"error": "Simulated error", "failed_step": failed_step},
    )

    res = await agent.process_message(msg, ctx)
    assert res.success is True
    assert res.data["decision"] == "replan"


@pytest.mark.asyncio
async def test_cognitive_coordinator_full_loop():
    event_bus = EventBus()
    negotiator = CapabilityNegotiator()
    negotiator.register_runtime("desktop", MockDesktopAdapter(event_bus))
    negotiator.register_runtime("vision", MockVisionAdapter())

    coordinator = CognitiveCoordinator(negotiator=negotiator)

    spec = GoalSpecification(description="Download and inspect revenue report", goal_type=GoalType.BROWSER)
    goal = Goal(spec=spec)
    ctx = SharedCognitiveContext(goal=goal)

    result = await coordinator.run_cognition_loop(ctx)

    assert result.success is True
    assert ctx.goal.state.value in ("completed", "ready")
    assert len(ctx.history) > 0
