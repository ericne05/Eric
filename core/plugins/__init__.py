"""
Eric Dynamic Plugin Loader System.

Public API::

    from core.plugins import IPlugin, PluginContext, PluginManifest, PluginState
    from core.plugins import IPluginManager
"""

from core.plugins.enums import PluginState
from core.plugins.exceptions import PluginDependencyError, PluginError, PluginLoadError, PluginManifestError
from core.plugins.interfaces import IPlugin, IPluginManager, PluginContext
from core.plugins.manager import PluginManager
from core.plugins.models import PluginManifest

__all__ = [
    "PluginState",
    "PluginContext",
    "IPlugin",
    "IPluginManager",
    "PluginManifest",
    "PluginManager",
    "PluginError",
    "PluginManifestError",
    "PluginDependencyError",
    "PluginLoadError",
]
