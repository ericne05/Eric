"""
Plugin System Exceptions.
"""


class PluginError(Exception):
    """Base exception for all plugin-related errors."""


class PluginManifestError(PluginError):
    """Raised when plugin.yaml is missing, invalid, or malformed."""


class PluginDependencyError(PluginError):
    """Raised when a plugin's dependency is missing or forms a circular cycle."""


class PluginLoadError(PluginError):
    """Raised when the plugin entry point cannot be imported or instantiated."""
