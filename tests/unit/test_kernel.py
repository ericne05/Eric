"""Unit tests for Kernel."""

from core.kernel.kernel import Kernel
from core.kernel.lifecycle import SystemState


class TestKernelLifecycle:
    """Verify Kernel transitions through correct lifecycle states."""

    def test_initial_state_is_created(self):
        kernel = Kernel(config={})
        assert kernel.state == SystemState.CREATED

    def test_boot_reaches_ready(self):
        kernel = Kernel(config={"app": {"name": "Eric"}})
        kernel.boot()
        assert kernel.state == SystemState.READY

    def test_shutdown_reaches_stopped(self):
        kernel = Kernel(config={})
        kernel.boot()
        kernel.shutdown()
        assert kernel.state == SystemState.STOPPED

    def test_full_lifecycle(self):
        """Boot then shutdown — verify the complete state chain."""
        kernel = Kernel(config={})

        assert kernel.state == SystemState.CREATED
        kernel.boot()
        assert kernel.state == SystemState.READY
        kernel.shutdown()
        assert kernel.state == SystemState.STOPPED


from core.config import SystemConfig

class TestKernelConfig:
    """Verify Kernel stores and exposes config correctly."""

    def test_config_is_accessible(self):
        cfg = {"app": {"name": "Eric", "version": "0.1.0"}}
        kernel = Kernel(config=cfg)
        assert isinstance(kernel.config, SystemConfig)
        assert kernel.config.app.name == "Eric"

    def test_empty_config(self):
        kernel = Kernel(config={})
        assert isinstance(kernel.config, SystemConfig)
        assert kernel.config.app.name == "Eric"  # Should use default

    def test_config_is_not_mutated_by_boot(self):
        cfg = {"app": {"name": "Eric"}}
        kernel = Kernel(config=cfg)
        kernel.boot()
        assert kernel.config.app.name == "Eric"


class TestKernelEventBus:
    """Verify Kernel integrates with EventBus correctly."""

    def test_event_bus_initialized_on_boot(self):
        kernel = Kernel(config={})
        assert kernel.event_bus is None
        kernel.boot()
        assert kernel.event_bus is not None

    def test_boot_emits_system_ready_event(self):
        kernel = Kernel(config={})
        kernel.boot()
        assert kernel.event_bus is not None
        events = [e for e in kernel.event_bus.history if e.name == "system.ready"]
        assert len(events) == 1
        assert events[0].source == "core.kernel"

    def test_shutdown_emits_system_shutdown_event(self):
        kernel = Kernel(config={})
        kernel.boot()

        published_events: list[str] = []
        if kernel.event_bus:
            kernel.event_bus.subscribe(
                "system.shutdown", lambda e: published_events.append(e.name)
            )

        kernel.shutdown()
        assert "system.shutdown" in published_events
        assert kernel.event_bus is None

