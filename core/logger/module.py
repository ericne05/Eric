"""
Logging Module Registration for DI Container.

Registers ILogger → LoggerManager as a singleton, configured from SystemConfig.
Loguru internals never leak outside this subsystem.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class LoggingModule(IDependencyModule):
    """
    Registers the logging subsystem into the DI Container.

    Maps ILogger interface → LoggerManager implementation.
    The factory resolves SystemConfig from the container to configure
    loguru sinks automatically.

    Usage::

        LoggingModule().register(container)
    """

    def register(self, container: "Container") -> None:
        from core.config.schemas import SystemConfig
        from core.logger.factory import setup_logger
        from core.logger.interface import ILogger

        container.add_singleton(
            ILogger,
            lambda c: setup_logger(c.resolve(SystemConfig).logging),
        )
