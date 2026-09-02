"""
Eric Dependency Injection Module.

Provides a lightweight, type-safe DI Container built on Python type hints.
Supports interface-based registration, auto constructor injection,
factory callables, three lifetime strategies, and lifecycle hooks.

Public API::

    from core.di import Container, Lifetime, Scope
    from core.di import IDependencyModule, ILifecycleAware
    from core.di import DIError, DependencyResolutionError, CircularDependencyError
"""

from core.di.container import Container
from core.di.enums import Lifetime
from core.di.exceptions import (
    CircularDependencyError,
    DependencyResolutionError,
    DIError,
)
from core.di.interfaces import IDependencyModule, ILifecycleAware
from core.di.provider import (
    Provider,
    ScopedProvider,
    SingletonProvider,
    TransientProvider,
)
from core.di.scope import Scope

__all__ = [
    "Container",
    "Lifetime",
    "Scope",
    "IDependencyModule",
    "ILifecycleAware",
    "DIError",
    "DependencyResolutionError",
    "CircularDependencyError",
    "Provider",
    "SingletonProvider",
    "TransientProvider",
    "ScopedProvider",
]
