"""
Plugin System Enums.

Defines the states a plugin can be in during its lifecycle.
"""

from enum import Enum


class PluginState(str, Enum):
    """
    Lifecycle states of a dynamic plugin.

    DISCOVERED: Manifest loaded and validated, but code not yet imported.
    LOADED: Code imported, instance created, DI module registered.
    INITIALIZED: Plugin's initialize() method called successfully.
    RUNNING: Plugin is active (typically after system.ready).
    STOPPED: Plugin's dispose() method called.
    FAILED: Plugin encountered an unrecoverable error during lifecycle.
    """

    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
