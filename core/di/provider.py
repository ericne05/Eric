"""
Dependency Injection Providers.

Each provider encapsulates a factory callable and a lifetime strategy.
Providers are responsible for creating and caching service instances.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, TYPE_CHECKING

from core.di.interfaces import ILifecycleAware

if TYPE_CHECKING:
    from core.di.container import Container
    from core.di.scope import Scope


class Provider(ABC):
    """
    Base class for all DI providers.

    A provider wraps a factory callable that accepts a Container (or Scope)
    and returns a service instance. The provider controls when and how
    often the factory is invoked.

    Args:
        factory: A callable ``(Container) -> instance`` that creates the service.
    """

    def __init__(self, factory: Callable[["Container"], Any]) -> None:
        self._factory = factory

    @abstractmethod
    def resolve(self, container: "Container | Scope") -> Any:
        """Resolve and return a service instance."""

    def dispose(self) -> None:
        """Release any cached resources. Override in subclasses."""


class SingletonProvider(Provider):
    """
    Lazy singleton: the factory is called once on first resolve(),
    and the same instance is returned thereafter.

    If the instance implements ILifecycleAware, initialize() is called
    immediately after construction.
    """

    def __init__(self, factory: Callable[["Container"], Any]) -> None:
        super().__init__(factory)
        self._instance: Any = None
        self._initialized: bool = False

    def resolve(self, container: "Container | Scope") -> Any:
        if not self._initialized:
            self._instance = self._factory(container)
            if isinstance(self._instance, ILifecycleAware):
                self._instance.initialize()
            self._initialized = True
        return self._instance

    def dispose(self) -> None:
        if self._initialized and isinstance(self._instance, ILifecycleAware):
            self._instance.dispose()
        self._instance = None
        self._initialized = False


class TransientProvider(Provider):
    """
    Creates a brand-new instance every time resolve() is called.

    If the instance implements ILifecycleAware, initialize() is called
    after each construction. Transient instances are NOT tracked for disposal
    by the container — the caller is responsible for their lifecycle.
    """

    def resolve(self, container: "Container | Scope") -> Any:
        instance = self._factory(container)
        if isinstance(instance, ILifecycleAware):
            instance.initialize()
        return instance

    def dispose(self) -> None:
        pass  # Transient instances are not tracked


class ScopedProvider(Provider):
    """
    One instance per Scope. The Scope object manages caching and disposal.

    When resolved from the root Container (outside any scope), behaves
    like a Singleton as a safe fallback.
    """

    def __init__(self, factory: Callable[["Container"], Any]) -> None:
        super().__init__(factory)
        # Fallback singleton for root-level resolution
        self._root_instance: Any = None
        self._root_initialized: bool = False

    def resolve(self, container: "Container | Scope") -> Any:
        from core.di.scope import Scope

        if isinstance(container, Scope):
            return container.resolve_scoped(self)

        # Fallback: resolve at root level acts as singleton
        if not self._root_initialized:
            self._root_instance = self._factory(container)
            if isinstance(self._root_instance, ILifecycleAware):
                self._root_instance.initialize()
            self._root_initialized = True
        return self._root_instance

    def create_instance(self, container: "Container | Scope") -> Any:
        """Create a fresh instance for a scope. Called by Scope internally."""
        instance = self._factory(container)
        if isinstance(instance, ILifecycleAware):
            instance.initialize()
        return instance

    def dispose(self) -> None:
        if self._root_initialized and isinstance(self._root_instance, ILifecycleAware):
            self._root_instance.dispose()
        self._root_instance = None
        self._root_initialized = False
