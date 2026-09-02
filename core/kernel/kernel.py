"""
Eric Kernel — Core system orchestrator.

Manages the initialization, lifecycle, and shutdown of all subsystems
following the System-Lifecycle specification.

Design decisions (see Decision-Log.md):
- NOT a Singleton — instantiated by Bootstrap for testability.
- Does NOT load .env or config — that is Bootstrap's responsibility.
- Orchestrates boot/shutdown sequence per System-Lifecycle.md.
- All services are resolved through the DI Container (Sprint 5).
"""

from core.config import SystemConfig
from core.di import Container
from core.events import Event, EventBus
from core.kernel.lifecycle import StateTransitionError, SystemState
from core.logger import ILogger


class Kernel:
    """
    Core system orchestrator for Eric.

    Receives pre-loaded configuration from Bootstrap and manages
    the lifecycle of all subsystems.
    """

    def __init__(self, config: SystemConfig | dict) -> None:
        """
        Initialize Kernel with pre-loaded configuration.

        Args:
            config: SystemConfig instance or dictionary.
        """
        # Support dict fallback for tests that manually inject config dictionaries
        if isinstance(config, dict):
            self._config = SystemConfig.from_dict(config)
        else:
            self._config = config
        self._state = SystemState.CREATED

        # Service references — populated during boot, used during shutdown.
        self._event_bus: EventBus | None = None
        self._logger: ILogger | None = None
        self._container = None
        self._service_registry = None
        self._plugin_loader = None

    # ── Public properties ────────────────────────────────

    @property
    def state(self) -> SystemState:
        """Current system state."""
        return self._state

    @property
    def config(self) -> SystemConfig:
        """Loaded system configuration."""
        return self._config

    @property
    def container(self) -> Container | None:
        """DI Container instance."""
        return self._container

    @property
    def event_bus(self) -> EventBus | None:
        """Loaded EventBus instance."""
        return self._event_bus

    @property
    def logger(self) -> ILogger | None:
        """Loaded ILogger instance."""
        return self._logger

    # ── Public lifecycle methods ─────────────────────────

    def boot(self) -> None:
        """
        Start the Kernel and boot all subsystems.
        Transitions: CREATED -> BOOTING -> READY.
        """
        if self._state != SystemState.CREATED:
            raise StateTransitionError(f"Cannot boot from state {self._state.name}")

        self._set_state(SystemState.BOOTING)

        try:
            # 1. Core Services & DI Container
            self._init_container()
            self._init_logger()
            self._init_event_bus()

            # 2. Storage & Memory
            self._init_memory()

            # 3. Discover & Load Plugins
            self._load_plugins()

            # 4. Initialize Services (Including Plugins)
            self._init_services()

            self._set_state(SystemState.READY)
            self._log("[Kernel] All subsystems initialized. System is ready.")

            # Emit system.ready event
            self._event_bus.publish_sync(
                Event.create(name="system.ready", source="system", payload={"version": "0.6.0"})
            )

        except Exception as e:
            self._set_state(SystemState.FAILED)
            if self._logger:
                self._logger.error(f"[Kernel] Boot failed: {e}", exc_info=True)
            raise RuntimeError(f"Kernel boot failed: {e}") from e

    def shutdown(self) -> None:
        """
        Gracefully shut down the system in reverse boot order.

        Container.dispose() handles lifecycle cleanup for all registered
        singleton services that implement ILifecycleAware.
        """
        self._set_state(SystemState.SHUTTING_DOWN)
        self._log("[Kernel] Shutdown sequence started...")

        self._unload_plugins()
        self._shutdown_services()
        self._shutdown_event_bus()
        self._shutdown_container()
        self._shutdown_logger()

        self._set_state(SystemState.STOPPED)
        print("[Kernel] System stopped.")

    # ── Private boot steps ───────────────────────────────

    def _init_container(self) -> None:
        """Sprint 5: Initialize DI Container and register core modules."""
        from core.config.module import ConfigModule
        from core.events.module import EventBusModule
        from core.logger.module import LoggingModule
        from core.memory.module import MemoryModule
        from core.plugins.module import PluginSystemModule
        from core.agents.module import AgentSystemModule

        self._container = Container()
        self._container.register_instance(Container, self._container)

        # Register modules — each subsystem registers itself
        ConfigModule(self._config).register(self._container)
        LoggingModule().register(self._container)
        EventBusModule().register(self._container)
        MemoryModule().register(self._container)
        PluginSystemModule().register(self._container)
        from core.tools.module import ToolSystemModule
        ToolSystemModule().register(self._container)
        from core.llm.module import LLMSystemModule
        LLMSystemModule().register(self._container)
        AgentSystemModule().register(self._container)
        from core.runtime.module import RuntimeModule
        RuntimeModule().register(self._container)

        self._log("[Kernel] DI Container initialized.")

    def _init_logger(self) -> None:
        """Sprint 3: Resolve Logger from DI Container."""
        self._logger = self._container.resolve(ILogger)
        self._log("[Kernel] Logger initialized.")

    def _init_event_bus(self) -> None:
        """Sprint 2: Resolve EventBus from DI Container."""
        self._log("[Kernel] Initializing Event Bus...")
        self._event_bus = self._container.resolve(EventBus)

    def _init_memory(self) -> None:
        """Sprint 6: Resolve MemoryService to force initialization."""
        self._log("[Kernel] Initializing Memory Engine...")
        from core.memory.interfaces import IMemoryService
        self._container.resolve(IMemoryService)

    def _load_plugins(self) -> None:
        """Sprint 7: Scan plugins/ and load enabled plugins."""
        self._log("[Kernel] Discovering and Loading Plugins...")
        from core.plugins.interfaces import IPluginManager
        plugin_manager = self._container.resolve(IPluginManager)
        plugin_manager.load_all()

    def _init_services(self) -> None:
        """Sprint 7: Initialize all loaded plugins and services."""
        self._log("[Kernel] Initializing Plugins and Services...")
        from core.plugins.interfaces import IPluginManager
        plugin_manager = self._container.resolve(IPluginManager)
        plugin_manager.initialize_all()

    # ── Private shutdown steps ───────────────────────────

    def _unload_plugins(self) -> None:
        self._log("[Kernel] Unloading Plugins... (TODO)")

    def _shutdown_services(self) -> None:
        self._log("[Kernel] Shutting down Services... (TODO)")

    def _shutdown_event_bus(self) -> None:
        if self._event_bus:
            self._log("[Kernel] Shutting down Event Bus...")
            shutdown_event = Event.create(
                name="system.shutdown",
                source="core.kernel",
                payload={"state": self._state.name},
            )
            self._event_bus.publish_sync(shutdown_event)
            self._event_bus.shutdown()
            self._event_bus = None

    def _shutdown_container(self) -> None:
        """Dispose all services managed by the DI Container."""
        if self._container:
            self._log("[Kernel] Disposing DI Container...")
            self._container.dispose()
            self._container = None

    def _shutdown_logger(self) -> None:
        if self._logger:
            self._log("[Kernel] Shutting down Logger...")
            self._logger.shutdown()
            self._logger = None

    # ── Internal helpers ─────────────────────────────────

    def _set_state(self, new_state: SystemState) -> None:
        """Transition to a new system state."""
        self._log(f"[Kernel] State: {self._state.name} -> {new_state.name}")
        self._state = new_state

    def _log(self, message: str) -> None:
        """Log a message. Uses Logger if available, falls back to print."""
        if self._logger:
            self._logger.info(message)
        else:
            print(message)
