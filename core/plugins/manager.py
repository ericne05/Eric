"""
Plugin Manager.

Responsible for discovering, resolving dependencies, loading,
and managing the lifecycle of all dynamic plugins.
"""

import importlib
import sys
from pathlib import Path

import yaml

from core.config.schemas import SystemConfig
from core.di.container import Container
from core.events.event_bus import EventBus
from core.logger.interface import ILogger
from core.plugins.enums import PluginState
from core.plugins.exceptions import PluginDependencyError, PluginLoadError, PluginManifestError
from core.plugins.interfaces import IPlugin, IPluginManager, PluginContext
from core.plugins.models import PluginManifest
from core.tools.interfaces import IToolRegistry


class PluginManager(IPluginManager):
    """
    Manages the dynamic discovery, loading, and execution of plugins.

    Implements a strict 7-step lifecycle:
    Discover -> Validate -> Dependency Sort -> Load -> Register -> Initialize -> Running
    """

    def __init__(
        self,
        config: SystemConfig,
        logger: ILogger,
        event_bus: EventBus,
        container: Container,
        tool_registry: IToolRegistry,
    ) -> None:
        self._config = config
        self._logger = logger
        self._event_bus = event_bus
        self._container = container
        self._tool_registry = tool_registry

        self._plugin_dir = Path(config.plugins.loader.get("plugin_dir", "./plugins")).resolve()
        
        # Track plugin state and data
        self._manifests: dict[str, PluginManifest] = {}
        self._states: dict[str, PluginState] = {}
        self._instances: dict[str, IPlugin] = {}

    def load_all(self) -> None:
        """Discover, sort, and load all enabled plugins."""
        if not self._config.plugins.loader.get("auto_load", True):
            self._logger.info("[PluginManager] auto_load is disabled. Skipping plugin discovery.")
            return

        self._logger.info(f"[PluginManager] Discovering plugins in {self._plugin_dir}...")
        self._discover()
        
        sorted_names = self._topological_sort()
        
        for name in sorted_names:
            self._load_plugin(name)

    def initialize_all(self) -> None:
        """Initialize all successfully loaded plugins."""
        for name, state in self._states.items():
            if state == PluginState.LOADED:
                self._initialize_plugin(name)

    def dispose_all(self) -> None:
        """Dispose all running plugins."""
        for name, state in list(self._states.items()):
            if state in (PluginState.INITIALIZED, PluginState.RUNNING):
                self._dispose_plugin(name)

    def get_plugin_state(self, name: str) -> PluginState | None:
        """Get the current lifecycle state of a plugin."""
        return self._states.get(name)

    def get_manifest(self, name: str) -> PluginManifest | None:
        """Get the manifest of a loaded plugin."""
        return self._manifests.get(name)

    # ── Internal Implementation ─────────────────────────────────────────

    def _discover(self) -> None:
        """Scan the plugin directory for valid plugin.yaml manifests."""
        if not self._plugin_dir.exists() or not self._plugin_dir.is_dir():
            self._logger.warning(f"[PluginManager] Plugin directory not found: {self._plugin_dir}")
            return

        for child in self._plugin_dir.iterdir():
            if child.is_dir():
                manifest_path = child / "plugin.yaml"
                if manifest_path.exists():
                    self._parse_manifest(manifest_path, child)

    def _parse_manifest(self, manifest_path: Path, plugin_dir: Path) -> None:
        """Parse a single plugin.yaml and update tracking dictionaries."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                raise PluginManifestError("Manifest must be a YAML dictionary.")

            manifest = PluginManifest.from_dict(data, plugin_dir=str(plugin_dir))
            
            # Check if enabled in its own manifest OR explicitly disabled in system config
            sys_registry = self._config.plugins.registry.get(manifest.name)
            sys_enabled = sys_registry.enabled if sys_registry else True
            
            if manifest.enabled and sys_enabled:
                if manifest.name in self._manifests:
                    self._logger.warning(f"[PluginManager] Duplicate plugin name '{manifest.name}'. Skipping {plugin_dir}.")
                    return
                
                self._manifests[manifest.name] = manifest
                self._states[manifest.name] = PluginState.DISCOVERED
                self._logger.debug(f"[PluginManager] Discovered: {manifest.name} v{manifest.version}")
            else:
                self._logger.debug(f"[PluginManager] Plugin '{manifest.name}' is disabled. Skipping.")
                
        except Exception as e:
            self._logger.error(f"[PluginManager] Failed to parse manifest at {manifest_path}: {e}")

    def _topological_sort(self) -> list[str]:
        """
        Sort plugins based on their dependencies (DAG).
        Raises PluginDependencyError on missing or circular dependencies.
        """
        in_degree = {name: 0 for name in self._manifests}
        graph: dict[str, list[str]] = {name: [] for name in self._manifests}
        
        # Build graph
        for name, manifest in self._manifests.items():
            for dep in manifest.dependencies:
                if dep not in self._manifests:
                    # Mark as failed
                    self._states[name] = PluginState.FAILED
                    raise PluginDependencyError(f"Plugin '{name}' requires missing dependency '{dep}'")
                
                graph[dep].append(name)
                in_degree[name] += 1

        # Kahn's algorithm
        # Tie-breaker: use 'priority' from manifest (lower value = higher priority)
        queue = [name for name, deg in in_degree.items() if deg == 0]
        # Sort queue by priority initially
        queue.sort(key=lambda n: self._manifests[n].priority)
        
        sorted_result = []
        
        while queue:
            # Re-sort queue in case new items were added, to maintain priority order
            queue.sort(key=lambda n: self._manifests[n].priority)
            current = queue.pop(0)
            sorted_result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(sorted_result) != len(self._manifests):
            # Find the nodes causing the cycle
            cycle_nodes = [node for node, deg in in_degree.items() if deg > 0]
            for node in cycle_nodes:
                self._states[node] = PluginState.FAILED
            raise PluginDependencyError(f"Circular dependency detected involving: {cycle_nodes}")

        return sorted_result

    def _load_plugin(self, name: str) -> None:
        """Dynamically import the plugin code and register its DI module."""
        manifest = self._manifests[name]
        
        # Ensure plugin directory is in sys.path so it can be imported
        # E.g. 'plugins/browser' -> we want 'plugins' in sys.path, or load 'browser.main' directly.
        # It's safer to ensure the parent of plugins_dir is in sys.path, 
        # but standard is to put the `plugins/` dir itself in sys.path, OR the project root.
        # Assuming the root dir (containing `plugins/`) is already in sys.path.
        
        plugin_root = str(self._plugin_dir)
        if plugin_root not in sys.path:
            sys.path.insert(0, plugin_root)

        try:
            # Format: "module.path:ClassName"
            if ":" not in manifest.entry:
                raise PluginLoadError(f"Invalid entry format '{manifest.entry}'. Expected 'module:Class'")
                
            module_path, class_name = manifest.entry.split(":", 1)
            
            # Import module
            module = importlib.import_module(module_path)
            
            # Get class
            plugin_class = getattr(module, class_name, None)
            if not plugin_class:
                raise PluginLoadError(f"Class '{class_name}' not found in module '{module_path}'")
                
            if not issubclass(plugin_class, IPlugin):
                raise PluginLoadError(f"Class '{class_name}' does not implement IPlugin")

            # Instantiate plugin (Plugins must have a zero-argument constructor)
            instance: IPlugin = plugin_class()
            self._instances[name] = instance
            
            # Register DI module if provided
            di_module = instance.module
            if di_module:
                di_module.register(self._container)
                
            self._states[name] = PluginState.LOADED
            self._logger.debug(f"[PluginManager] Loaded: {name}")
            
        except Exception as e:
            self._states[name] = PluginState.FAILED
            self._logger.error(f"[PluginManager] Failed to load plugin '{name}': {e}")
            # If a load fails, dependent plugins will fail during initialize phase.

    def _initialize_plugin(self, name: str) -> None:
        """Call plugin.initialize() with PluginContext."""
        instance = self._instances[name]
        
        # Check dependencies state
        manifest = self._manifests[name]
        for dep in manifest.dependencies:
            if self._states.get(dep) not in (PluginState.INITIALIZED, PluginState.RUNNING):
                self._states[name] = PluginState.FAILED
                self._logger.error(f"[PluginManager] Cannot initialize '{name}': dependency '{dep}' is not ready.")
                return

        context = PluginContext(
            logger=self._logger,
            event_bus=self._event_bus,
            config=self._config,
            tool_registry=self._tool_registry,
        )
        
        try:
            instance.initialize(context)
            self._states[name] = PluginState.RUNNING
            self._logger.info(f"[PluginManager] Plugin '{name}' is running.")
            
            # Emit loaded event
            from core.events import Event
            self._event_bus.publish_sync(Event.create(
                name="plugin.system.loaded",
                source="system",
                payload={"plugin_name": name, "version": manifest.version}
            ))
            
        except Exception as e:
            self._states[name] = PluginState.FAILED
            self._logger.error(f"[PluginManager] Failed to initialize plugin '{name}': {e}")

    def _dispose_plugin(self, name: str) -> None:
        """Call plugin.dispose()."""
        instance = self._instances.get(name)
        if instance:
            try:
                instance.dispose()
                self._states[name] = PluginState.STOPPED
                self._logger.debug(f"[PluginManager] Plugin '{name}' stopped.")

                from core.events import Event
                self._event_bus.publish_sync(Event.create(
                    name="plugin.system.unloaded",
                    source="system",
                    payload={"plugin_name": name}
                ))
                
            except Exception as e:
                self._states[name] = PluginState.FAILED
                self._logger.error(f"[PluginManager] Error disposing plugin '{name}': {e}")
