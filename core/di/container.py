"""
Dependency Injection Container.

The central registry and resolution engine for Eric's service architecture.
Supports interface-based registration, auto constructor injection,
factory callables, optional dependencies, and lifecycle management.

Architecture constraint: Only Kernel/Bootstrap should call resolve() directly.
All other services receive dependencies via constructor injection.
"""

import inspect
import types
from typing import Any, Callable, get_type_hints

from core.di.enums import Lifetime
from core.di.exceptions import (
    CircularDependencyError,
    DependencyResolutionError,
)
from core.di.interfaces import ILifecycleAware
from core.di.provider import (
    Provider,
    ScopedProvider,
    SingletonProvider,
    TransientProvider,
)
from core.di.scope import Scope


class Container:
    """
    Lightweight DI Container with interface-based registration,
    auto constructor injection, and lifecycle management.

    Usage::

        container = Container()

        # Interface → Implementation (recommended)
        container.add_singleton(ILogger, LoggerManager)

        # Factory-based registration
        container.add_singleton(ILogger, lambda c: LoggerManager.configure(...))

        # Pre-built instance
        container.register_instance(SystemConfig, config)

        # Resolution (Kernel/Bootstrap only)
        logger = container.resolve(ILogger)

        # Scoped services
        scope = container.create_scope()
        session = scope.resolve(ISession)
        scope.dispose()

        # Shutdown
        container.dispose()
    """

    def __init__(self) -> None:
        self._registry: dict[type, Provider] = {}
        self._resolving: list[type] = []  # Resolution stack for circular detection
        self._disposed: bool = False

    # ── Registration API ─────────────────────────────────────────────

    def register(
        self,
        interface: type,
        implementation: type | Callable[["Container"], Any] | None = None,
        lifetime: Lifetime = Lifetime.SINGLETON,
    ) -> None:
        """
        Register a service with the container.

        Args:
            interface: The type (or interface) to register under.
            implementation: The concrete class or factory callable.
                           If None, interface is used as implementation.
            lifetime: The service lifetime strategy.
        """
        if self._disposed:
            raise RuntimeError("Cannot register on a disposed Container.")

        factory = self._build_factory(interface, implementation)
        provider = self._create_provider(factory, lifetime)
        self._registry[interface] = provider

    def register_instance(self, interface: type, instance: Any) -> None:
        """
        Register a pre-built instance as a singleton.

        The instance will be returned directly on every resolve() call.
        No factory is invoked, and initialize() is NOT called
        (the caller already constructed the object).
        """
        if self._disposed:
            raise RuntimeError("Cannot register on a disposed Container.")

        provider = SingletonProvider(lambda _c: instance)
        # Mark as already initialized so factory is never called
        provider._instance = instance
        provider._initialized = True
        self._registry[interface] = provider

    def add_singleton(
        self,
        interface: type,
        implementation: type | Callable[["Container"], Any] | None = None,
    ) -> None:
        """DSL shortcut: register as Singleton."""
        self.register(interface, implementation, Lifetime.SINGLETON)

    def add_transient(
        self,
        interface: type,
        implementation: type | Callable[["Container"], Any] | None = None,
    ) -> None:
        """DSL shortcut: register as Transient."""
        self.register(interface, implementation, Lifetime.TRANSIENT)

    def add_scoped(
        self,
        interface: type,
        implementation: type | Callable[["Container"], Any] | None = None,
    ) -> None:
        """DSL shortcut: register as Scoped."""
        self.register(interface, implementation, Lifetime.SCOPED)

    # ── Resolution API ───────────────────────────────────────────────

    def resolve(self, interface: type) -> Any:
        """
        Resolve a service by its registered interface.

        Auto-injects constructor dependencies by inspecting type hints.
        Detects circular dependencies and reports the full resolution chain.

        Args:
            interface: The type (or interface) to resolve.

        Returns:
            The resolved service instance.

        Raises:
            DependencyResolutionError: If the service is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        if self._disposed:
            raise RuntimeError("Cannot resolve from a disposed Container.")

        provider = self._get_provider(interface)
        return provider.resolve(self)

    def has(self, interface: type) -> bool:
        """Check whether a service is registered for the given interface."""
        return interface in self._registry

    # ── Scope API ────────────────────────────────────────────────────

    def create_scope(self) -> Scope:
        """
        Create a child scope for managing scoped service lifetimes.

        Returns:
            A new Scope instance bound to this Container.
        """
        if self._disposed:
            raise RuntimeError("Cannot create scope from a disposed Container.")
        return Scope(self)

    # ── Lifecycle API ────────────────────────────────────────────────

    def dispose(self) -> None:
        """
        Dispose all singleton and scoped providers, releasing resources.

        Calls dispose() on every ILifecycleAware singleton in reverse
        registration order. After disposal, the container cannot be used.
        """
        if self._disposed:
            return

        # Dispose in reverse registration order
        for provider in reversed(list(self._registry.values())):
            provider.dispose()

        self._registry.clear()
        self._disposed = True

    # ── Internal Methods ─────────────────────────────────────────────

    def _get_provider(self, interface: type) -> Provider:
        """Look up the provider for an interface, raising if not found."""
        if interface not in self._registry:
            raise DependencyResolutionError(
                f"Service '{interface.__name__}' is not registered in the container."
            )
        return self._registry[interface]

    def _build_factory(
        self,
        interface: type,
        implementation: type | Callable[["Container"], Any] | None,
    ) -> Callable[["Container"], Any]:
        """
        Build a factory callable from the given implementation.

        If implementation is:
        - None: use interface as the concrete class, auto-inject constructor.
        - A callable (lambda/function): use it directly as the factory.
        - A class: wrap it in an auto-injecting factory.
        """
        if implementation is None:
            implementation = interface

        # If it's already a factory callable (lambda, function), use directly
        if callable(implementation) and not isinstance(implementation, type):
            return implementation

        # It's a class — build an auto-injecting factory
        cls = implementation
        return lambda container: self._auto_construct(cls, container)

    def _auto_construct(self, cls: type, container: "Container | Scope") -> Any:
        """
        Construct a class by inspecting its __init__ type hints and
        resolving each dependency from the container.

        Supports optional dependencies (Type | None = None).
        """
        # Detect circular dependency
        if cls in self._resolving:
            chain = self._resolving + [cls]
            raise CircularDependencyError(chain)

        self._resolving.append(cls)
        try:
            hints = self._get_constructor_hints(cls)
            kwargs: dict[str, Any] = {}

            sig = inspect.signature(cls.__init__)
            for param_name, param_type in hints.items():
                param = sig.parameters.get(param_name)
                is_optional = self._is_optional_type(param_type, param)

                # Skip primitive types with defaults — they are config params, not services
                if self._is_primitive(param_type) and param is not None and param.default is not param.empty:
                    continue

                # Unwrap Optional[X] → X
                resolved_type = self._unwrap_optional(param_type)

                if resolved_type is not None and self.has(resolved_type):
                    kwargs[param_name] = self.resolve(resolved_type)
                elif is_optional:
                    kwargs[param_name] = None
                elif param is not None and param.default is not param.empty:
                    # Use the parameter's default value
                    continue
                else:
                    raise DependencyResolutionError(
                        f"Cannot resolve parameter '{param_name}: {param_type}' "
                        f"for '{cls.__name__}'. "
                        f"Service '{param_type.__name__ if hasattr(param_type, '__name__') else param_type}' "
                        f"is not registered."
                    )

            return cls(**kwargs)
        finally:
            self._resolving.pop()

    def _get_constructor_hints(self, cls: type) -> dict[str, type]:
        """
        Extract type hints from __init__, excluding 'self' and 'return'.
        """
        try:
            hints = get_type_hints(cls.__init__)
        except Exception:
            hints = {}

        hints.pop("return", None)
        return hints

    def _is_optional_type(self, type_hint: Any, param: inspect.Parameter | None) -> bool:
        """
        Check if a type hint represents an optional dependency.

        Matches:
        - X | None
        - Optional[X]
        - Parameter with default value of None
        """
        # Check for default=None
        if param is not None and param.default is None:
            return True

        # Check for Union types containing None (X | None, Optional[X])
        origin = getattr(type_hint, "__origin__", None)
        if origin is types.UnionType or origin is type(int | str):
            args = getattr(type_hint, "__args__", ())
            return type(None) in args

        # Python 3.10+ X | None
        if isinstance(type_hint, types.UnionType):
            return type(None) in type_hint.__args__

        return False

    def _unwrap_optional(self, type_hint: Any) -> type | None:
        """
        Unwrap Optional[X] or X | None to get X.

        Returns None if the type cannot be unwrapped to a concrete type.
        """
        origin = getattr(type_hint, "__origin__", None)
        args = getattr(type_hint, "__args__", ())

        # Handle Union types (Optional[X] = Union[X, None], or X | None)
        if origin is types.UnionType or isinstance(type_hint, types.UnionType):
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return non_none[0]
            return None

        # Plain type
        if isinstance(type_hint, type):
            return type_hint

        return None

    _PRIMITIVE_TYPES = frozenset({int, float, str, bool, bytes})

    def _is_primitive(self, type_hint: Any) -> bool:
        """Check if a type hint is a primitive (non-injectable) type."""
        return isinstance(type_hint, type) and type_hint in self._PRIMITIVE_TYPES

    def _create_provider(
        self, factory: Callable[["Container"], Any], lifetime: Lifetime
    ) -> Provider:
        """Create the appropriate Provider for the given lifetime."""
        if lifetime == Lifetime.SINGLETON:
            return SingletonProvider(factory)
        elif lifetime == Lifetime.TRANSIENT:
            return TransientProvider(factory)
        elif lifetime == Lifetime.SCOPED:
            return ScopedProvider(factory)
        else:
            raise ValueError(f"Unknown lifetime: {lifetime}")
