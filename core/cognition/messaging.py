"""
Cognitive Message Bus & Router.
"""

from typing import Callable, Dict, List, Optional

from core.cognition.enums import AgentRole
from core.cognition.models import AgentMessage


class CognitiveMessageBus:
    """
    Message bus enabling structured Agent-to-Agent message passing.
    """

    def __init__(self):
        self._listeners: Dict[AgentRole, List[Callable]] = {}

    def subscribe(self, role: AgentRole, callback: Callable) -> None:
        if role not in self._listeners:
            self._listeners[role] = []
        self._listeners[role].append(callback)

    async def send_message(self, message: AgentMessage) -> None:
        target = message.target_role
        callbacks = self._listeners.get(target, [])
        for cb in callbacks:
            await cb(message)
