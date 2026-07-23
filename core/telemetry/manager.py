"""
InMemory Telemetry Manager.
"""

from typing import Any, Dict, List

from core.logger.interface import ILogger
from core.telemetry.interfaces import ITelemetryManager


class InMemoryTelemetryManager(ITelemetryManager):
    """
    A simple telemetry manager that logs metrics and events.
    In a real OS, this would push to Prometheus, Datadog, or an OpenTelemetry collector.
    """
    def __init__(self, logger: ILogger):
        self._logger = logger
        self.metrics: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

    def record_metric(self, name: str, value: float, tags: Dict[str, str] | None = None) -> None:
        self.metrics.append({"name": name, "value": value, "tags": tags})
        self._logger.debug(f"[Telemetry] Metric '{name}': {value} (tags: {tags})")

    def record_event(self, name: str, data: Dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "data": data})
        self._logger.debug(f"[Telemetry] Event '{name}': {data}")
