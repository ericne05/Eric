"""
Error & Recovery Diagnostic Panel Component.
Displays deep diagnostic recovery trace: Selector not found -> Recovery -> Vision fallback -> Retry 2 -> Completed.
"""

from dataclasses import dataclass, field
import datetime
from typing import List


@dataclass
class DiagnosticStep:
    label: str
    status: str  # 'failed', 'recovery', 'fallback', 'retry', 'completed'
    details: str = ""
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class ErrorDiagnosticPanel:
    """
    Error & Recovery Diagnostic Visualization Widget.
    """

    def __init__(self):
        self._trace: List[DiagnosticStep] = []

    def record_step(self, label: str, status: str, details: str = "") -> DiagnosticStep:
        step = DiagnosticStep(label=label, status=status, details=details)
        self._trace.append(step)
        return step

    def get_trace(self) -> List[DiagnosticStep]:
        return list(self._trace)

    def clear(self) -> None:
        self._trace.clear()
