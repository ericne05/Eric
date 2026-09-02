"""
Config Module Registration for DI Container.

Registers SystemConfig as a pre-built singleton instance.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.config.schemas import SystemConfig
    from core.di.container import Container


class ConfigModule(IDependencyModule):
    """
    Registers the application's SystemConfig into the DI Container.

    Since SystemConfig is loaded from YAML files during bootstrap
    (before the container exists), it is registered as a pre-built instance.

    Usage::

        config = ConfigService().load_from_dir(config_dir)
        ConfigModule(config).register(container)
    """

    def __init__(self, config: "SystemConfig") -> None:
        self._config = config

    def register(self, container: "Container") -> None:
        from core.config.schemas import SystemConfig

        container.register_instance(SystemConfig, self._config)
