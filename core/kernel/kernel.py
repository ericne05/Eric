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
from core.kernel.lifecycle import SystemState
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
        Boot the system following System-Lifecycle sequence.

        Order (Sprint 5 — Container-based):
            1. Initialize DI Container & register modules
            2. Resolve Logger from Container
            3. Resolve EventBus from Container
            4. Load Plugins
            5. Register Services
            6. Emit system.ready
        """
        self._set_state(SystemState.BOOTING)

        self._init_container()
        self._init_logger()
        self._init_event_bus()
        self._load_plugins()
        self._register_services()

        self._set_state(SystemState.READY)
        self._log("[Kernel] All subsystems initialized. System is ready.")

        if self._event_bus:
            ready_event = Event.create(
                name="system.ready",
                source="core.kernel",
                payload={"state": self._state.name},
            )
            self._event_bus.publish_sync(ready_event)

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

        self._container = Container()

        # Register modules — each subsystem registers itself
        ConfigModule(self._config).register(self._container)
        LoggingModule().register(self._container)
        EventBusModule().register(self._container)
        MemoryModule().register(self._container)

        self._log("[Kernel] DI Container initialized.")

    def _init_logger(self) -> None:
        """Sprint 3: Resolve Logger from DI Container."""
        self._logger = self._container.resolve(ILogger)
        self._log("[Kernel] Logger initialized.")

    def _init_event_bus(self) -> None:
        """Sprint 2: Resolve EventBus from DI Container."""
        self._log("[Kernel] Initializing Event Bus...")
        self._event_bus = self._container.resolve(EventBus)

    def _load_plugins(self) -> None:
        """Sprint 7: Scan plugins/ and load enabled plugins."""
        self._log("[Kernel] Loading Plugins... (TODO)")

    def _register_services(self) -> None:
        """Sprint 6: Register tools and agents into Service Registry."""
        self._log("[Kernel] Registering Services... (TODO)")

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
