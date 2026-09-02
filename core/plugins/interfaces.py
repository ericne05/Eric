"""
Plugin System Interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.config.schemas import SystemConfig
from core.di.interfaces import IDependencyModule
from core.events import EventBus
from core.logger.interface import ILogger
from core.plugins.enums import PluginState
from core.plugins.models import PluginManifest
from core.tools.interfaces import IToolRegistry


@dataclass(frozen=True)
class PluginContext:
    """
    Context injected into a plugin during initialization.

    Provides safe access to core subsystems without exposing
    the raw DI Container (avoiding Service Locator anti-pattern).
    If a plugin needs other services, it should register its own
    dependencies via its IDependencyModule.
    """

    logger: ILogger
    event_bus: EventBus
    config: SystemConfig
    tool_registry: IToolRegistry


class IPlugin(ABC):
    """
    Contract for all Eric dynamic plugins.

    Plugins must implement this interface and be exported via
    the 'entry' point specified in plugin.yaml.
    """

    @property
    @abstractmethod
    def module(self) -> IDependencyModule | None:
        """
        Return the DI registration module for this plugin, if any.
        Called by PluginManager after instantiation, before initialize().
        """

    @abstractmethod
    def initialize(self, context: PluginContext) -> None:
        """
        Initialize the plugin.

        Called by PluginManager after the plugin's DI module has been registered.
        """

    @abstractmethod
    def dispose(self) -> None:
        """
        Clean up resources before the plugin is stopped.
        """


class IPluginManager(ABC):
    """
    Contract for the Plugin Loader/Manager subsystem.
    """

    @abstractmethod
    def load_all(self) -> None:
        """Discover, sort, and load all enabled plugins from the configured directory."""

    @abstractmethod
    def initialize_all(self) -> None:
        """Initialize all successfully loaded plugins."""

    @abstractmethod
    def dispose_all(self) -> None:
        """Dispose all running plugins."""

    @abstractmethod
    def get_plugin_state(self, name: str) -> PluginState | None:
        """Get the current lifecycle state of a plugin."""

    @abstractmethod
    def get_manifest(self, name: str) -> PluginManifest | None:
        """Get the manifest of a loaded plugin."""
