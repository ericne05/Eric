"""
Plugin System Module Registration.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class PluginSystemModule(IDependencyModule):
    """
    Registers the PluginManager into the DI Container.
    """

    def register(self, container: "Container") -> None:
        from core.plugins.interfaces import IPluginManager
        from core.plugins.manager import PluginManager

        from core.config.schemas import SystemConfig
        from core.logger.interface import ILogger
        from core.events.event_bus import EventBus
        from core.tools.interfaces import IToolRegistry
        
        def _manager_factory(c):
            return PluginManager(
                config=c.resolve(SystemConfig),
                logger=c.resolve(ILogger),
                event_bus=c.resolve(EventBus),
                container=c,
                tool_registry=c.resolve(IToolRegistry),
            )
        container.add_singleton(IPluginManager, _manager_factory)
