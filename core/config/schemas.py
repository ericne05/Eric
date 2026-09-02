"""
Configuration Schemas.

Defines immutable, type-safe @dataclass structures for all system configurations.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

from core.config.exceptions import SchemaValidationError


@dataclass(frozen=True)
class BaseSchema:
    """Base schema providing dictionary conversion and validation."""

    def validate(self) -> None:
        """Override to implement custom validation logic."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseSchema":
        """Instantiate the schema from a dictionary."""
        # This base from_dict handles nested instantiation by looking at __annotations__
        # For simplicity in this project, we manually parse nested schemas in specific from_dict overrides
        # where nested dataclasses are present, to avoid complex reflection logic.
        return cls(**data)


# ---------------------------------------------------------------------------
# 1. App Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StorageConfig(BaseSchema):
    base_path: str = "./storage"
    database_path: str = "./storage/database/eric.db"
    vector_path: str = "./storage/vector"
    logs_path: str = "./storage/logs"

    def validate(self) -> None:
        if not self.base_path:
            raise SchemaValidationError("Storage base_path cannot be empty.")

@dataclass(frozen=True)
class AppConfig(BaseSchema):
    name: str = "Eric"
    version: str = "0.1.0"
    environment: str = "development"
    storage: StorageConfig = field(default_factory=StorageConfig)

    def validate(self) -> None:
        if self.environment not in ("development", "staging", "production"):
            raise SchemaValidationError(f"Invalid environment: {self.environment}")
        self.storage.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        storage_data = data.pop("storage", {})
        return cls(
            storage=StorageConfig(**storage_data),
            **data
        )


# ---------------------------------------------------------------------------
# 2. Logging Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LoggingConfig(BaseSchema):
    # This stores the raw dict layout as it maps exactly to Python's logging dictConfig schema
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Any] = field(default_factory=dict)
    handlers: Dict[str, Any] = field(default_factory=dict)
    loggers: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.version != 1:
            raise SchemaValidationError("Logging version must be 1.")


# ---------------------------------------------------------------------------
# 3. Agents Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AgentItemConfig(BaseSchema):
    enabled: bool = True
    module_path: str = ""
    # Store any additional specific config for an agent
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.enabled and not self.module_path:
            raise SchemaValidationError("Enabled agent must have a module_path.")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentItemConfig":
        enabled = data.pop("enabled", True)
        module_path = data.pop("module_path", "")
        return cls(enabled=enabled, module_path=module_path, extra=data)

@dataclass(frozen=True)
class AgentsConfig(BaseSchema):
    agents: Dict[str, AgentItemConfig] = field(default_factory=dict)

    def validate(self) -> None:
        for name, agent in self.agents.items():
            agent.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentsConfig":
        agents_data = data.get("agents", {})
        agents = {k: AgentItemConfig.from_dict(v) for k, v in agents_data.items()}
        return cls(agents=agents)


# ---------------------------------------------------------------------------
# 4. Browser Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BrowserConfig(BaseSchema):
    provider: str = "playwright"
    executable_path: str = ""
    user_data_dir: str = "./storage/cache/browser_profile"
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 800})
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    network: Dict[str, Any] = field(default_factory=dict)
    download: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.provider not in ("playwright", "selenium", "puppeteer"):
            raise SchemaValidationError(f"Invalid browser provider: {self.provider}")
        if self.viewport.get("width", 0) <= 0 or self.viewport.get("height", 0) <= 0:
            raise SchemaValidationError("Browser viewport dimensions must be positive integers.")


# ---------------------------------------------------------------------------
# 5. LLM Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LLMConfig(BaseSchema):
    default_provider: str = "gemini"
    default_model: str = "gemini-2.5-flash"
    providers: Dict[str, Any] = field(default_factory=lambda: {"gemini": {}})

    def validate(self) -> None:
        if self.default_provider not in self.providers:
            raise SchemaValidationError(f"Default provider '{self.default_provider}' not configured.")


# ---------------------------------------------------------------------------
# 6. Memory Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MemoryConfig(BaseSchema):
    short_term: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)
    vector_store: Dict[str, Any] = field(default_factory=dict)
    consolidation: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.long_term.get("provider") not in ("sqlite",):
            # As per configs, sqlite is currently allowed
            pass


# ---------------------------------------------------------------------------
# 7. Plugins Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PluginItemConfig(BaseSchema):
    enabled: bool = False
    priority: int = 10
    config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginItemConfig":
        return cls(**data)

@dataclass(frozen=True)
class PluginsConfig(BaseSchema):
    loader: Dict[str, Any] = field(default_factory=lambda: {"auto_load": True, "plugin_dir": "./plugins", "allow_unverified_plugins": False})
    registry: Dict[str, PluginItemConfig] = field(default_factory=dict)

    def validate(self) -> None:
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginsConfig":
        registry_data = data.get("registry", {})
        registry = {k: PluginItemConfig.from_dict(v) for k, v in registry_data.items()}
        return cls(loader=data.get("loader", {}), registry=registry)


# ---------------------------------------------------------------------------
# 8. Scheduler Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SchedulerConfig(BaseSchema):
    core: Dict[str, Any] = field(default_factory=lambda: {"max_workers": 4, "timezone": "Asia/Ho_Chi_Minh"})
    tasks: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.core.get("max_workers", 0) <= 0:
            raise SchemaValidationError("Scheduler max_workers must be > 0.")


# ---------------------------------------------------------------------------
# 9. Security Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SecurityConfig(BaseSchema):
    sandbox: Dict[str, Any] = field(default_factory=dict)
    redaction: Dict[str, Any] = field(default_factory=dict)
    permission_gates: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        pass


# ---------------------------------------------------------------------------
# 10. Voice Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VoiceConfig(BaseSchema):
    stt: Dict[str, Any] = field(default_factory=dict)
    tts: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Root System Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SystemConfig(BaseSchema):
    """Aggregate of all top-level configurations."""
    app: AppConfig = field(default_factory=AppConfig)
    agents: AgentsConfig = field(default_factory=AgentsConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)

    def validate(self) -> None:
        """Validates all nested configurations."""
        self.app.validate()
        self.agents.validate()
        self.browser.validate()
        self.llm.validate()
        self.logging.validate()
        self.memory.validate()
        self.plugins.validate()
        self.scheduler.validate()
        self.security.validate()
        self.voice.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemConfig":
        return cls(
            app=AppConfig.from_dict(data.get("app", {})),
            agents=AgentsConfig.from_dict(data), # "agents" is nested in root config file as "agents" dict or top level in agents.yaml
            browser=BrowserConfig.from_dict(data.get("browser", {})),
            llm=LLMConfig.from_dict(data.get("llm", {})),
            logging=LoggingConfig.from_dict(data.get("logging", {})),
            memory=MemoryConfig.from_dict(data.get("memory", {})),
            plugins=PluginsConfig.from_dict(data.get("plugins", {})),
            scheduler=SchedulerConfig.from_dict(data.get("scheduler", {})),
            security=SecurityConfig.from_dict(data.get("security", {})),
            voice=VoiceConfig.from_dict(data.get("voice", {}))
        )
