"""
Agent Registry Implementation.
"""

from typing import Any

from core.agents.interfaces import IAgent, IAgentRegistry


class AgentRegistry(IAgentRegistry):
    """
    In-memory registry for available Agents.
    """

    def __init__(self) -> None:
        self._agents: dict[str, IAgent] = {}

    def register(self, agent: IAgent) -> None:
        """Register a new Agent."""
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' is already registered.")
        self._agents[agent.name] = agent

    def get_agent(self, name: str) -> IAgent | None:
        """Retrieve an Agent by name."""
        return self._agents.get(name)

    def get_all(self) -> list[IAgent]:
        """Return a list of all registered Agents."""
        return list(self._agents.values())
