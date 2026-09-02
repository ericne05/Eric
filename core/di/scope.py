"""
Dependency Injection Scope.

A Scope is a child context of a Container that manages its own set of
scoped service instances. Scoped instances are isolated between scopes
and disposed when the scope ends.
"""

from typing import Any, TYPE_CHECKING

from core.di.interfaces import ILifecycleAware

if TYPE_CHECKING:
    from core.di.container import Container
    from core.di.provider import ScopedProvider


class Scope:
    """
    A child container that manages scoped service lifetimes.

    - SCOPED services: one instance per Scope, cached here.
    - SINGLETON services: delegated to the parent Container.
    - TRANSIENT services: delegated to the parent Container (new each time).

    Usage::

        scope = container.create_scope()
        try:
            session = scope.resolve(ISession)
            # ... use session ...
        finally:
            scope.dispose()
    """

    def __init__(self, parent: "Container") -> None:
        self._parent = parent
        self._scoped_instances: dict[type, Any] = {}
        self._disposed: bool = False

    @property
    def parent(self) -> "Container":
        """The parent Container this scope was created from."""
        return self._parent

    def resolve(self, interface: type) -> Any:
        """
        Resolve a service within this scope.

        Scoped services are cached per-scope. Singleton and Transient
        services are delegated to the parent Container.
        """
        if self._disposed:
            raise RuntimeError("Cannot resolve from a disposed Scope.")

        from core.di.provider import ScopedProvider

        provider = self._parent._get_provider(interface)
        if isinstance(provider, ScopedProvider):
            return self.resolve_scoped(provider, interface)

        # Singleton and Transient: delegate to parent
        return provider.resolve(self._parent)

    def resolve_scoped(
        self, provider: "ScopedProvider", interface: type | None = None
    ) -> Any:
        """
        Resolve a scoped service, caching the instance in this scope.

        Called internally by ScopedProvider.resolve() or Scope.resolve().
        """
        # Find the interface key for this provider
        if interface is None:
            interface = self._find_interface_for_provider(provider)

        if interface not in self._scoped_instances:
            instance = provider.create_instance(self)
            self._scoped_instances[interface] = instance

        return self._scoped_instances[interface]

    def _find_interface_for_provider(self, provider: "ScopedProvider") -> type:
        """Reverse-lookup the interface registered for a given provider."""
        for iface, prov in self._parent._registry.items():
            if prov is provider:
                return iface
        raise RuntimeError("Provider not found in parent container registry.")

    def dispose(self) -> None:
        """
        Dispose all scoped instances and mark this scope as ended.

        Calls dispose() on any instance that implements ILifecycleAware.
        Does NOT affect the parent Container or its singletons.
        """
        if self._disposed:
            return

        for instance in reversed(list(self._scoped_instances.values())):
            if isinstance(instance, ILifecycleAware):
                instance.dispose()

        self._scoped_instances.clear()
        self._disposed = True
