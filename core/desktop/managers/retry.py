"""
Pluggable Retry Strategies for Desktop Runtime.
"""

from abc import ABC, abstractmethod


class IRetryStrategy(ABC):
    """Interface for retry delay calculations."""

    @abstractmethod
    def calculate_delay_seconds(self, attempt: int, base_delay: float = 1.0) -> float:
        pass


class FixedRetry(IRetryStrategy):
    """Fixed delay strategy."""

    def calculate_delay_seconds(self, attempt: int, base_delay: float = 1.0) -> float:
        return base_delay


class LinearRetry(IRetryStrategy):
    """Linear delay strategy (delay = attempt * base_delay)."""

    def calculate_delay_seconds(self, attempt: int, base_delay: float = 1.0) -> float:
        return attempt * base_delay


class ExponentialRetry(IRetryStrategy):
    """Exponential backoff delay strategy (delay = (2 ** (attempt - 1)) * base_delay)."""

    def calculate_delay_seconds(self, attempt: int, base_delay: float = 1.0) -> float:
        return (2 ** max(0, attempt - 1)) * base_delay
