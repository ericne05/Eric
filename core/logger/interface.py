"""
Abstract interface for Logger in Eric.

Defines the contract for all logger implementations following Enterprise standards.
"""

from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    """
    Abstract Base Class for Logger implementations.

    Provides standard log levels and structured context binding.
    """

    @abstractmethod
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        pass

    @abstractmethod
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        pass

    @abstractmethod
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        pass

    @abstractmethod
    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        pass

    @abstractmethod
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        pass

    @abstractmethod
    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception message with traceback information."""
        pass

    @abstractmethod
    def bind(self, **kwargs: Any) -> "ILogger":
        """
        Return a logger instance bound with structured context fields.

        Args:
            **kwargs: Key-value pairs (e.g., module, correlation_id, agent).

        Returns:
            An ILogger instance with bound context.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Flush and release all log sinks."""
        pass
