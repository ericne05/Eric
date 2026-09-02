"""
Mock Goal Adapter for Unit Testing.
"""

from core.events.event_bus import EventBus
from core.goals.managers.goal_manager import GoalManager
from core.runtime.capability import CapabilityNegotiator


class MockGoalAdapter:
    """
    Mock Goal Adapter wrapping GoalManager and a CapabilityNegotiator.
    """

    def __init__(self, negotiator: CapabilityNegotiator, event_bus: EventBus):
        self.negotiator = negotiator
        self.event_bus = event_bus
        self.manager = GoalManager(negotiator=negotiator, event_bus=event_bus)
