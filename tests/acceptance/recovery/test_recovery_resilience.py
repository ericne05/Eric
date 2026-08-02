"""
Recovery & Resilience Acceptance Tests (Window Interruption, Process Crash, Recovery).
"""

import pytest

from core.cognition import AgentMessage, AgentRole, MessageType, RecoveryAgent, SharedCognitiveContext
from core.goals import Goal, GoalSpecification, ExecutionStep, ExecutionPlan


@pytest.mark.asyncio
async def test_recovery_resilience_workflow():
    """
    Workflow: Window Closed -> Exception Triggered -> RecoveryAgent Re-evaluates -> Replan / Recover
    """
    agent = RecoveryAgent()
    spec = GoalSpecification(description="Interrupted action recovery")
    goal = Goal(spec=spec)
    step = ExecutionStep(action_name="click_button")
    goal.plan = ExecutionPlan(steps=[step])

    ctx = SharedCognitiveContext(goal=goal)
    msg = AgentMessage(
        sender_role=AgentRole.EXECUTION,
        target_role=AgentRole.RECOVERY,
        message_type=MessageType.RECOVERY_PROPOSAL,
        payload={"error": "Window unexpectedly closed", "failed_step": step},
    )

    res = await agent.process_message(msg, ctx)
    assert res.success is True
    assert res.data["decision"] in ("replan", "retry")
