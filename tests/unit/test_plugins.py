"""
Unit tests for the Plugin System (Sprint 7).
"""

import sys
from pathlib import Path

import pytest

from core.config.schemas import SystemConfig
from core.di.container import Container
from core.di.interfaces import IDependencyModule
from core.events import EventBus
from core.logger.interface import ILogger
from core.plugins.enums import PluginState
from core.plugins.exceptions import PluginDependencyError, PluginLoadError, PluginManifestError
from core.plugins.interfaces import IPlugin, PluginContext
from core.plugins.manager import PluginManager
from core.plugins.models import PluginManifest
from core.tools.registry import ToolRegistry


# ── Mocks & Stubs ────────────────────────────────────────────────────────


class MockLogger(ILogger):
    def debug(self, msg: str, **kwargs) -> None: pass
    def info(self, msg: str, **kwargs) -> None: pass
    def warning(self, msg: str, **kwargs) -> None: pass
    def error(self, msg: str, exc_info=None, **kwargs) -> None: print(f"ERROR: {msg}")
    def exception(self, msg: str, exc_info=None, **kwargs) -> None: print(f"EXCEPTION: {msg}")
    def critical(self, msg: str, exc_info=None, **kwargs) -> None: pass
    def shutdown(self) -> None: pass
    def bind(self, **kwargs) -> "ILogger": return self


class MockDIModule(IDependencyModule):
    def register(self, container: Container) -> None:
        # Just a mock
        pass


class MockPlugin(IPlugin):
    def __init__(self):
        self.is_initialized = False
        self.is_disposed = False
        self._module = MockDIModule()

    @property
    def module(self) -> IDependencyModule | None:
        return self._module

    def initialize(self, context: PluginContext) -> None:
        self.is_initialized = True

    def dispose(self) -> None:
        self.is_disposed = True


class BadPluginInit(MockPlugin):
    def initialize(self, context: PluginContext) -> None:
        raise RuntimeError("Crash on init!")


# ── Manifest Tests ───────────────────────────────────────────────────────


class TestPluginManifest:
    def test_valid_manifest(self):
        data = {
            "name": "test_plugin",
            "version": "1.0.0",
            "entry": "test_plugin.main:Plugin",
            "priority": 10,
            "dependencies": ["memory"]
        }
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == "test_plugin"
        assert manifest.priority == 10
        assert "memory" in manifest.dependencies

    def test_missing_required_fields_raises(self):
        data = {"name": "test_plugin"}  # missing version and entry
        with pytest.raises(PluginManifestError):
            PluginManifest.from_dict(data)


# ── PluginManager Tests ──────────────────────────────────────────────────


class TestPluginManager:
    @pytest.fixture
    def setup_manager(self, tmp_path):
        """Creates a PluginManager and a temporary plugin directory."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # We need to add the tmp_path to sys.path so dynamic imports work in tests
        if str(tmp_path) not in sys.path:
            sys.path.insert(0, str(tmp_path))

        config = SystemConfig()
        # Override config.plugins.loader.plugin_dir using __dict__ mutation (it's frozen)
        # Actually SystemConfig is frozen, so we have to recreate it or modify carefully.
        # We can just pass a modified config if needed, but for now we'll mock the manager's _plugin_dir.
        
        logger = MockLogger()
        event_bus = EventBus()
        container = Container()
        tool_registry = ToolRegistry()

        manager = PluginManager(config, logger, event_bus, container, tool_registry)
        # Force the plugin dir to our tmp_path
        manager._plugin_dir = plugins_dir
        
        yield manager, plugins_dir
        
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))

    def _create_plugin_files(self, plugin_dir: Path, name: str, entry_code: str, manifest_yaml: str):
        """Helper to create a fake plugin package."""
        p_dir = plugin_dir / name
        p_dir.mkdir(parents=True, exist_ok=True)
        
        # plugin.yaml
        (p_dir / "plugin.yaml").write_text(manifest_yaml, encoding="utf-8")
        
        # Python code
        (p_dir / "__init__.py").write_text("", encoding="utf-8")
        (p_dir / "main.py").write_text(entry_code, encoding="utf-8")

    def test_discover_and_load_valid_plugin(self, setup_manager):
        manager, plugins_dir = setup_manager
        
        manifest = f"""
name: valid_plugin
version: 1.0.0
entry: valid_plugin.main:MyPlugin
"""
        code = """
from core.plugins.interfaces import IPlugin, PluginContext

class MyPlugin(IPlugin):
    @property
    def module(self): return None
    def initialize(self, context: PluginContext): pass
    def dispose(self): pass
"""
        self._create_plugin_files(plugins_dir, "valid_plugin", code, manifest)
        
        manager.load_all()
        assert manager.get_plugin_state("valid_plugin") == PluginState.LOADED
        
        manager.initialize_all()
        assert manager.get_plugin_state("valid_plugin") == PluginState.RUNNING

    def test_dependency_sorting(self, setup_manager):
        manager, plugins_dir = setup_manager
        
        # A depends on B
        a_manifest = "name: A\nversion: 1\nentry: A.main:Plugin\ndependencies: ['B']"
        b_manifest = "name: B\nversion: 1\nentry: B.main:Plugin"
        
        code = "from tests.unit.test_plugins import MockPlugin as Plugin\n"
        
        self._create_plugin_files(plugins_dir, "A", code, a_manifest)
        self._create_plugin_files(plugins_dir, "B", code, b_manifest)
        
        manager._discover()
        sorted_plugins = manager._topological_sort()
        
        # B must be loaded before A
        assert sorted_plugins == ["B", "A"]

    def test_circular_dependency_raises(self, setup_manager):
        manager, plugins_dir = setup_manager
        
        a_manifest = "name: A\nversion: 1\nentry: A.main:Plugin\ndependencies: ['B']"
        b_manifest = "name: B\nversion: 1\nentry: B.main:Plugin\ndependencies: ['A']"
        
        self._create_plugin_files(plugins_dir, "A", "", a_manifest)
        self._create_plugin_files(plugins_dir, "B", "", b_manifest)
        
        manager._discover()
        with pytest.raises(PluginDependencyError, match="Circular dependency"):
            manager._topological_sort()
            
        assert manager.get_plugin_state("A") == PluginState.FAILED

    def test_missing_dependency_raises(self, setup_manager):
        manager, plugins_dir = setup_manager
        
        a_manifest = "name: A\nversion: 1\nentry: A.main:Plugin\ndependencies: ['MISSING']"
        self._create_plugin_files(plugins_dir, "A", "", a_manifest)
        
        manager._discover()
        with pytest.raises(PluginDependencyError, match="requires missing dependency"):
            manager._topological_sort()

    def test_plugin_init_failure_does_not_crash_system(self, setup_manager):
        manager, plugins_dir = setup_manager
        
        manifest = "name: crash_plugin\nversion: 1\nentry: crash_plugin.main:Plugin"
        code = "from tests.unit.test_plugins import BadPluginInit as Plugin\n"
        
        self._create_plugin_files(plugins_dir, "crash_plugin", code, manifest)
        
        # Shouldn't crash
        manager.load_all()
        manager.initialize_all()
        
        # Should be marked as failed
        assert manager.get_plugin_state("crash_plugin") == PluginState.FAILED

    def test_dispose_all(self, setup_manager):
        manager, plugins_dir = setup_manager
        
        manifest = "name: ok_plugin\nversion: 1\nentry: ok_plugin.main:Plugin"
        code = "from tests.unit.test_plugins import MockPlugin as Plugin\n"
        self._create_plugin_files(plugins_dir, "ok_plugin", code, manifest)
        
        manager.load_all()
        manager.initialize_all()
        assert manager.get_plugin_state("ok_plugin") == PluginState.RUNNING
        
        manager.dispose_all()
        assert manager.get_plugin_state("ok_plugin") == PluginState.STOPPED
