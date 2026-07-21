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


class TestKernelConfig:
    """Verify Kernel stores and exposes config correctly."""

    def test_config_is_accessible(self):
        cfg = {"app": {"name": "Eric", "version": "0.1.0"}}
        kernel = Kernel(config=cfg)
        assert kernel.config == cfg

    def test_empty_config(self):
        kernel = Kernel(config={})
        assert kernel.config == {}

    def test_config_is_not_mutated_by_boot(self):
        cfg = {"app": {"name": "Eric"}}
        kernel = Kernel(config=cfg)
        kernel.boot()
        assert kernel.config["app"]["name"] == "Eric"
