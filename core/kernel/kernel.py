"""
Eric Kernel — Core system orchestrator.

Manages the initialization, lifecycle, and shutdown of all subsystems
following the System-Lifecycle specification.

Design decisions (see Decision-Log.md):
- NOT a Singleton — instantiated by Bootstrap for testability.
- Does NOT load .env or config — that is Bootstrap's responsibility.
- Orchestrates boot/shutdown sequence per System-Lifecycle.md.
- Uses print() as fallback until Logger module is implemented.
"""

from core.events import Event, EventBus
from core.kernel.lifecycle import SystemState
from core.logger import ILogger, setup_logger


class Kernel:
    """
    Core system orchestrator for Eric.

    Receives pre-loaded configuration from Bootstrap and manages
    the lifecycle of all subsystems.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize Kernel with pre-loaded configuration.

        Args:
            config: Dictionary of all loaded YAML configs.
                    Keys are config filenames without extension
                    (e.g., "app", "llm", "memory").
        """
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
    def config(self) -> dict:
        """Loaded system configuration."""
        return self._config

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

        Order:
            1. Initialize Logger
            2. Initialize Event Bus
            3. Initialize DI Container
            4. Load Plugins
            5. Register Services
            6. Emit system.ready
        """
        self._set_state(SystemState.BOOTING)

        self._init_logger()
        self._init_event_bus()
        self._init_container()
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
        """
        self._set_state(SystemState.SHUTTING_DOWN)
        self._log("[Kernel] Shutdown sequence started...")

        self._unload_plugins()
        self._shutdown_services()
        self._shutdown_event_bus()
        self._shutdown_logger()

        self._set_state(SystemState.STOPPED)
        print("[Kernel] System stopped.")

    # ── Private boot steps ───────────────────────────────

    def _init_logger(self) -> None:
        """Sprint 3: Initialize Logger from configs/logging.yaml."""
        logging_cfg = self._config.get("logging", {})
        self._logger = setup_logger(logging_cfg)
        self._log("[Kernel] Logger initialized.")

    def _init_event_bus(self) -> None:
        """Sprint 2: Initialize async Event Bus."""
        self._log("[Kernel] Initializing Event Bus...")
        self._event_bus = EventBus()

    def _init_container(self) -> None:
        """Sprint 5: Initialize DI Container and register base services."""
        self._log("[Kernel] Initializing DI Container... (TODO)")

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
