"""Unit tests for Bootstrap."""

import os
from pathlib import Path

import yaml

from core.kernel.lifecycle import SystemState
from core.kernel.bootstrap import bootstrap
from core.config import SystemConfig


class TestBootstrapIntegration:
    """Verify full bootstrap() produces a booted Kernel."""

    def test_bootstrap_returns_ready_kernel(self, tmp_path):
        # Create a minimal config directory
        (tmp_path / "app.yaml").write_text(
            "app:\n  name: Eric\n",
            encoding="utf-8",
        )

        kernel = bootstrap(project_root=tmp_path, config_dir=tmp_path)
        assert kernel.state == SystemState.READY
        assert isinstance(kernel.config, SystemConfig)
        assert kernel.config.app.name == "Eric"
