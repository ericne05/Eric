"""
Logger Factory and InterceptHandler for Eric.

Provides setup_logger factory and standard library logging redirection.
"""

import logging
from typing import Any

from loguru import logger as _loguru_logger

from core.logger.interface import ILogger
from core.logger.manager import LoggerManager


class InterceptHandler(logging.Handler):
    """
    Redirect standard library `logging` messages to loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: Any = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


from core.config.schemas import LoggingConfig


def setup_logger(config: LoggingConfig | dict) -> ILogger:
    """
    Factory function to initialize and configure the logging subsystem.

    Redirects Python's standard `logging` to loguru and configures LoggerManager sinks.

    Args:
        config: Logging configuration instance or dictionary.

    Returns:
        Configured ILogger instance.
    """
    # Intercept standard logging messages
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Configure sinks via LoggerManager
    return LoggerManager.configure(config)
