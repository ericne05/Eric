"""
Telemetry Interfaces.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ITelemetryManager(ABC):
    """
    Manager for recording system metrics and events.
    """
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Dict[str, str] | None = None) -> None:
        """Record a numerical metric (e.g., latency, token count)."""
        pass

    @abstractmethod
    def record_event(self, name: str, data: Dict[str, Any] | None = None) -> None:
        """Record a system event (e.g., tool started, LLM error)."""
        pass
