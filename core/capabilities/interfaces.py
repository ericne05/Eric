"""
Capabilities Interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class Capability:
    name: str
    description: str
    version: str


class ICapabilityRegistry(ABC):
    """
    Registry for system capabilities (e.g., vision, voice, browser).
    """
    @abstractmethod
    def register(self, capability: Capability) -> None:
        pass

    @abstractmethod
    def get_all(self) -> List[Capability]:
        pass

    @abstractmethod
    def has_capability(self, name: str) -> bool:
        pass
