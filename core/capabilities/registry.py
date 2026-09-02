"""
Dynamic Capability Registry Implementation.
"""

from typing import List

from core.capabilities.interfaces import Capability, ICapabilityRegistry


class DynamicCapabilityRegistry(ICapabilityRegistry):
    def __init__(self):
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """Register a new capability dynamically."""
        self._capabilities[capability.name] = capability

    def unregister(self, name: str) -> None:
        """Remove a capability dynamically (e.g. when a plugin unloads)."""
        if name in self._capabilities:
            del self._capabilities[name]

    def get_all(self) -> List[Capability]:
        return list(self._capabilities.values())

    def has_capability(self, name: str) -> bool:
        return name in self._capabilities
