"""
Eric Logger Module.

Provides ILogger interface, LoggerManager implementation, and setup_logger factory.
"""

from core.logger.factory import setup_logger
from core.logger.interface import ILogger
from core.logger.manager import LoggerManager

__all__ = [
    "ILogger",
    "LoggerManager",
    "setup_logger",
]
