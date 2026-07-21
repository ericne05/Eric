"""Unit tests for Bootstrap."""

import os
from pathlib import Path

import yaml

from core.kernel.bootstrap import load_configs, resolve_env_vars
from core.kernel.lifecycle import SystemState


class TestLoadConfigs:
    """Verify YAML config loading."""

    def test_loads_valid_yaml(self, tmp_path):
        (tmp_path / "app.yaml").write_text(
            "app:\n  name: Eric\n  version: 0.1.0\n",
            encoding="utf-8",
        )
        configs = load_configs(tmp_path)
        assert "app" in configs
        assert configs["app"]["app"]["name"] == "Eric"

    def test_missing_directory_returns_empty(self, tmp_path):
        configs = load_configs(tmp_path / "nonexistent")
        assert configs == {}

    def test_empty_yaml_returns_empty_dict(self, tmp_path):
        (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
        configs = load_configs(tmp_path)
        assert configs["empty"] == {}

    def test_multiple_files_sorted(self, tmp_path):
        (tmp_path / "b.yaml").write_text("key: b\n", encoding="utf-8")
        (tmp_path / "a.yaml").write_text("key: a\n", encoding="utf-8")
        configs = load_configs(tmp_path)
        assert list(configs.keys()) == ["a", "b"]


class TestResolveEnvVars:
    """Verify ${ENV_VAR} placeholder resolution."""

    def test_resolves_string(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "secret123")
        result = resolve_env_vars({"api_key": "${MY_KEY}"})
        assert result["api_key"] == "secret123"

    def test_unresolved_keeps_placeholder(self):
        result = resolve_env_vars({"api_key": "${UNKNOWN_VAR}"})
        assert result["api_key"] == "${UNKNOWN_VAR}"

    def test_nested_dict(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "localhost")
        config = {"db": {"host": "${DB_HOST}", "port": 5432}}
        result = resolve_env_vars(config)
        assert result["db"]["host"] == "localhost"
        assert result["db"]["port"] == 5432

    def test_list_values(self, monkeypatch):
        monkeypatch.setenv("ITEM", "resolved")
        result = resolve_env_vars(["${ITEM}", "static"])
        assert result == ["resolved", "static"]

    def test_non_string_passthrough(self):
        result = resolve_env_vars({"count": 42, "flag": True})
        assert result == {"count": 42, "flag": True}


class TestBootstrapIntegration:
    """Verify full bootstrap() produces a booted Kernel."""

    def test_bootstrap_returns_ready_kernel(self, tmp_path):
        # Create a minimal config directory
        (tmp_path / "app.yaml").write_text(
            "app:\n  name: Eric\n",
            encoding="utf-8",
        )
        from core.kernel.bootstrap import bootstrap

        kernel = bootstrap(project_root=tmp_path, config_dir=tmp_path)
        assert kernel.state == SystemState.READY
        assert kernel.config["app"]["app"]["name"] == "Eric"
