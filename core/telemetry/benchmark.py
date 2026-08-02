"""
Telemetry Benchmark Suite for Eric (Sprint 14.5 Product-Grade v1.0).
Measures exact millisecond performance for core operations.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BenchmarkMetric:
    """A single timing measurement."""
    operation_name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class BenchmarkSuite:
    """
    Performance Benchmark Monitor.
    Tracks timing (in ms) for:
      - Goal Creation
      - Planning Time
      - Runtime Dispatch
      - Vision OCR
      - Desktop Click
      - Browser Action
      - Memory Write
      - Total Goal Time
    """

    def __init__(self):
        self._metrics: List[BenchmarkMetric] = []

    def record(self, operation_name: str, duration_ms: float) -> None:
        self._metrics.append(BenchmarkMetric(operation_name=operation_name, duration_ms=round(duration_ms, 2)))

    def measure(self, operation_name: str):
        """Context manager helper for timing operations."""
        class _Timer:
            def __init__(self, suite, name):
                self.suite = suite
                self.name = name
                self.start_time = 0

            def __enter__(self):
                self.start_time = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
                self.suite.record(self.name, elapsed_ms)

        return _Timer(self, operation_name)

    def get_benchmark_report(self) -> Dict[str, Dict[str, float]]:
        """
        Calculates average, min, max timing for all recorded operations.
        Returns dict: { operation_name -> { 'avg_ms': X, 'min_ms': Y, 'max_ms': Z, 'count': N } }
        """
        grouped: Dict[str, List[float]] = {}
        for m in self._metrics:
            if m.operation_name not in grouped:
                grouped[m.operation_name] = []
            grouped[m.operation_name].append(m.duration_ms)

        report = {}
        for op, values in grouped.items():
            report[op] = {
                "avg_ms": round(sum(values) / len(values), 2),
                "min_ms": round(min(values), 2),
                "max_ms": round(max(values), 2),
                "count": len(values),
            }
        return report

    def reset(self) -> None:
        self._metrics.clear()
