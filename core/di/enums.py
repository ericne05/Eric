"""
Dependency Injection Lifetime Enums.

Defines the lifecycle strategies for service registrations.
"""

from enum import Enum


class Lifetime(Enum):
    """
    Specifies how a service instance is managed by the DI Container.

    SINGLETON: One instance shared across the entire application lifetime.
               Created lazily on first resolve().
    TRANSIENT: A new instance is created every time resolve() is called.
    SCOPED:    One instance per Scope. Shared within a scope, isolated between scopes.
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"
