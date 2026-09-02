"""
LoggerManager implementation wrapping loguru.

Provides concrete implementation of ILogger contract without exposing loguru directly.
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

from core.logger.interface import ILogger


class LoggerManager(ILogger):
    """
    Concrete Logger implementation using loguru as underlying backend.

    Implements ILogger interface, managing sinks (Console, File) and
    providing structured context binding.
    """

    def __init__(self, _logger_handle: Any = None) -> None:
        """
        Initialize LoggerManager.

        Args:
            _logger_handle: Internal loguru logger handle. If None, uses base loguru logger.
        """
        self._inner_logger = _logger_handle if _logger_handle is not None else _loguru_logger

    # ── Factory / Sink Setup ─────────────────────────────

    @classmethod
    def configure(cls, config: "LoggingConfig | dict") -> "LoggerManager":
        """
        Configure loguru sinks according to configuration dictionary or LoggingConfig.

        Args:
            config: Logging configuration.

        Returns:
            Configured LoggerManager instance.
        """
        # Reset existing loguru sinks
        _loguru_logger.remove()

        if isinstance(config, dict):
            logging_cfg = config.get("logging", config)
            handlers_cfg = logging_cfg.get("handlers", {})
        else:
            handlers_cfg = config.handlers

        # 1. Console Sink
        console_cfg = handlers_cfg.get("console", {})
        console_level = console_cfg.get("level", "DEBUG")
        _loguru_logger.add(
            sys.stdout,
            level=console_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            enqueue=True,
        )

        # 2. File Sink
        file_cfg = handlers_cfg.get("file", {})
        log_file_path = file_cfg.get("filename", "./storage/logs/eric.log")
        file_level = file_cfg.get("level", "INFO")
        max_bytes = file_cfg.get("maxBytes", 10485760)
        backup_count = file_cfg.get("backupCount", 5)
        encoding = file_cfg.get("encoding", "utf8")

        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _loguru_logger.add(
            str(log_path),
            level=file_level,
            rotation=max_bytes,
            retention=backup_count,
            encoding=encoding,
            enqueue=True,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        )

        return cls(_loguru_logger)

    # ── ILogger Implementation ───────────────────────────

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._inner_logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self._inner_logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._inner_logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self._inner_logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        self._inner_logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception message with traceback."""
        self._inner_logger.exception(message, *args, **kwargs)

    def bind(self, **kwargs: Any) -> ILogger:
        """Return a new LoggerManager instance bound with extra context fields."""
        bound_handle = self._inner_logger.bind(**kwargs)
        return LoggerManager(bound_handle)

    def shutdown(self) -> None:
        """Remove loguru sinks and flush logs."""
        _loguru_logger.remove()
