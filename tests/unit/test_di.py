"""
Unit tests for the Dependency Injection Container (Sprint 5).
"""

from abc import ABC, abstractmethod

import pytest

from core.di import (
    CircularDependencyError,
    Container,
    DependencyResolutionError,
    IDependencyModule,
    ILifecycleAware,
    Lifetime,
)


# ── Test Fixtures & Helpers ──────────────────────────────────────────────


class IDatabase(ABC):
    @abstractmethod
    def query(self, sql: str) -> str: ...


class SqlDatabase(IDatabase):
    def query(self, sql: str) -> str:
        return f"SQL: {sql}"


class ICache(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...


class MemoryCache(ICache):
    def get(self, key: str) -> str | None:
        return None


class ServiceA:
    """Service with no dependencies."""

    pass


class ServiceB:
    """Service that depends on ServiceA."""

    def __init__(self, a: ServiceA) -> None:
        self.a = a


class ServiceC:
    """Service that depends on ServiceA and ServiceB."""

    def __init__(self, a: ServiceA, b: ServiceB) -> None:
        self.a = a
        self.b = b


class ServiceWithOptional:
    """Service with an optional dependency."""

    def __init__(self, a: ServiceA, cache: ICache | None = None) -> None:
        self.a = a
        self.cache = cache


class CircularA:
    def __init__(self, b: "CircularB") -> None:
        self.b = b


class CircularB:
    def __init__(self, a: CircularA) -> None:
        self.a = a


class CircularX:
    def __init__(self, y: "CircularY") -> None:
        self.y = y


class CircularY:
    def __init__(self, z: "CircularZ") -> None:
        self.z = z


class CircularZ:
    def __init__(self, x: CircularX) -> None:
        self.x = x


class LifecycleService(ILifecycleAware):
    initialized: bool = False
    disposed: bool = False

    def initialize(self) -> None:
        self.initialized = True

    def dispose(self) -> None:
        self.disposed = True


class LifecycleTracker(ILifecycleAware):
    """Tracks the order of lifecycle calls."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def initialize(self) -> None:
        self.calls.append("initialize")

    def dispose(self) -> None:
        self.calls.append("dispose")


@pytest.fixture
def container():
    return Container()


# ── Singleton Tests ──────────────────────────────────────────────────────


class TestSingleton:
    def test_singleton_returns_same_instance(self, container):
        container.add_singleton(ServiceA)
        a1 = container.resolve(ServiceA)
        a2 = container.resolve(ServiceA)
        assert a1 is a2

    def test_lazy_singleton_not_created_until_resolve(self, container):
        """Singleton is lazy — factory is NOT called at registration time."""
        call_count = 0

        def factory(c):
            nonlocal call_count
            call_count += 1
            return ServiceA()

        container.add_singleton(ServiceA, factory)
        assert call_count == 0  # Not yet created
        container.resolve(ServiceA)
        assert call_count == 1  # Created on first resolve
        container.resolve(ServiceA)
        assert call_count == 1  # Still only one creation


# ── Transient Tests ──────────────────────────────────────────────────────


class TestTransient:
    def test_transient_returns_new_instance_each_time(self, container):
        container.add_transient(ServiceA)
        a1 = container.resolve(ServiceA)
        a2 = container.resolve(ServiceA)
        assert a1 is not a2


# ── Scoped Tests ─────────────────────────────────────────────────────────


class TestScoped:
    def test_scoped_returns_same_instance_within_scope(self, container):
        container.add_scoped(ServiceA)
        scope = container.create_scope()
        a1 = scope.resolve(ServiceA)
        a2 = scope.resolve(ServiceA)
        assert a1 is a2

    def test_different_scopes_get_different_instances(self, container):
        container.add_scoped(ServiceA)
        scope1 = container.create_scope()
        scope2 = container.create_scope()
        a1 = scope1.resolve(ServiceA)
        a2 = scope2.resolve(ServiceA)
        assert a1 is not a2

    def test_scope_inherits_parent_singletons(self, container):
        container.add_singleton(ServiceA)
        scope = container.create_scope()
        a_root = container.resolve(ServiceA)
        a_scope = scope.resolve(ServiceA)
        assert a_root is a_scope


# ── Interface Mapping Tests ──────────────────────────────────────────────


class TestInterfaceMapping:
    def test_resolve_by_interface(self, container):
        container.add_singleton(IDatabase, SqlDatabase)
        db = container.resolve(IDatabase)
        assert isinstance(db, SqlDatabase)
        assert db.query("SELECT 1") == "SQL: SELECT 1"

    def test_swap_implementation(self, container):
        """Registering same interface twice overwrites the first."""
        container.add_singleton(IDatabase, SqlDatabase)

        class MockDatabase(IDatabase):
            def query(self, sql: str) -> str:
                return "MOCK"

        container.add_singleton(IDatabase, MockDatabase)
        db = container.resolve(IDatabase)
        assert isinstance(db, MockDatabase)


# ── Auto Constructor Injection Tests ─────────────────────────────────────


class TestAutoInjection:
    def test_inject_single_dependency(self, container):
        container.add_singleton(ServiceA)
        container.add_singleton(ServiceB)
        b = container.resolve(ServiceB)
        assert isinstance(b.a, ServiceA)

    def test_inject_multiple_dependencies(self, container):
        container.add_singleton(ServiceA)
        container.add_singleton(ServiceB)
        container.add_singleton(ServiceC)
        c = container.resolve(ServiceC)
        assert isinstance(c.a, ServiceA)
        assert isinstance(c.b, ServiceB)
        assert c.b.a is c.a  # Same singleton instance

    def test_no_dependency_constructor(self, container):
        container.add_singleton(ServiceA)
        a = container.resolve(ServiceA)
        assert isinstance(a, ServiceA)


# ── Optional Dependency Tests ────────────────────────────────────────────


class TestOptionalDependency:
    def test_optional_resolved_as_none_when_not_registered(self, container):
        container.add_singleton(ServiceA)
        container.add_singleton(ServiceWithOptional)
        svc = container.resolve(ServiceWithOptional)
        assert svc.a is not None
        assert svc.cache is None

    def test_optional_resolved_when_registered(self, container):
        container.add_singleton(ServiceA)
        container.add_singleton(ICache, MemoryCache)
        container.add_singleton(ServiceWithOptional)
        svc = container.resolve(ServiceWithOptional)
        assert isinstance(svc.cache, MemoryCache)


# ── Factory Registration Tests ───────────────────────────────────────────


class TestFactoryRegistration:
    def test_lambda_factory(self, container):
        container.add_singleton(IDatabase, lambda c: SqlDatabase())
        db = container.resolve(IDatabase)
        assert isinstance(db, SqlDatabase)

    def test_factory_receives_container(self, container):
        container.add_singleton(ServiceA)
        container.add_singleton(
            ServiceB, lambda c: ServiceB(a=c.resolve(ServiceA))
        )
        b = container.resolve(ServiceB)
        assert isinstance(b.a, ServiceA)


# ── register_instance Tests ─────────────────────────────────────────────


class TestRegisterInstance:
    def test_register_prebuilt_instance(self, container):
        instance = ServiceA()
        container.register_instance(ServiceA, instance)
        resolved = container.resolve(ServiceA)
        assert resolved is instance


# ── Circular Dependency Tests ────────────────────────────────────────────


class TestCircularDependency:
    def test_direct_circular_raises_error(self, container):
        container.add_singleton(CircularA)
        container.add_singleton(CircularB)
        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(CircularA)
        assert "CircularA" in str(exc_info.value)
        assert "CircularB" in str(exc_info.value)

    def test_deep_circular_chain_reported(self, container):
        container.add_singleton(CircularX)
        container.add_singleton(CircularY)
        container.add_singleton(CircularZ)
        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(CircularX)
        msg = str(exc_info.value)
        assert "CircularX" in msg
        assert "CircularY" in msg
        assert "CircularZ" in msg

    def test_circular_chain_attribute(self, container):
        container.add_singleton(CircularA)
        container.add_singleton(CircularB)
        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(CircularA)
        chain_names = [t.__name__ for t in exc_info.value.chain]
        assert chain_names[0] == chain_names[-1]  # Cycle detected


# ── Missing Registration Tests ───────────────────────────────────────────


class TestMissingRegistration:
    def test_unregistered_service_raises(self, container):
        with pytest.raises(DependencyResolutionError, match="ServiceA"):
            container.resolve(ServiceA)

    def test_has_returns_false_for_unregistered(self, container):
        assert container.has(ServiceA) is False

    def test_has_returns_true_for_registered(self, container):
        container.add_singleton(ServiceA)
        assert container.has(ServiceA) is True


# ── Lifecycle Hook Tests ─────────────────────────────────────────────────


class TestLifecycleHooks:
    def test_initialize_called_on_first_resolve(self, container):
        container.add_singleton(LifecycleService)
        svc = container.resolve(LifecycleService)
        assert svc.initialized is True

    def test_dispose_called_on_container_dispose(self, container):
        container.add_singleton(LifecycleService)
        svc = container.resolve(LifecycleService)
        container.dispose()
        assert svc.disposed is True

    def test_lifecycle_order_initialize_before_dispose(self, container):
        container.add_singleton(LifecycleTracker)
        tracker = container.resolve(LifecycleTracker)
        container.dispose()
        assert tracker.calls == ["initialize", "dispose"]

    def test_scope_dispose_calls_lifecycle_dispose(self, container):
        container.add_scoped(LifecycleService)
        scope = container.create_scope()
        svc = scope.resolve(LifecycleService)
        assert svc.initialized is True
        scope.dispose()
        assert svc.disposed is True


# ── DSL Method Tests ─────────────────────────────────────────────────────


class TestDSLMethods:
    def test_add_singleton_registers_singleton(self, container):
        container.add_singleton(ServiceA)
        a1 = container.resolve(ServiceA)
        a2 = container.resolve(ServiceA)
        assert a1 is a2

    def test_add_transient_registers_transient(self, container):
        container.add_transient(ServiceA)
        a1 = container.resolve(ServiceA)
        a2 = container.resolve(ServiceA)
        assert a1 is not a2

    def test_add_scoped_registers_scoped(self, container):
        container.add_scoped(ServiceA)
        scope = container.create_scope()
        a1 = scope.resolve(ServiceA)
        a2 = scope.resolve(ServiceA)
        assert a1 is a2


# ── Module Registration Tests ────────────────────────────────────────────


class TestModuleRegistration:
    def test_module_registers_services(self, container):
        class TestModule(IDependencyModule):
            def register(self, container):
                container.add_singleton(ServiceA)
                container.add_singleton(ServiceB)

        TestModule().register(container)
        b = container.resolve(ServiceB)
        assert isinstance(b.a, ServiceA)
