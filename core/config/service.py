"""
Configuration Service & Loader.

Provides the facade for loading, resolving, building, and validating configurations.
Implements a pipeline pattern: Parser -> EnvResolver -> SchemaBuilder -> Validator -> Cache.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from core.config.exceptions import ConfigError
from core.config.parsers import YAMLParser, JSONParser, BaseParser
from core.config.resolvers import EnvResolver
from core.config.schemas import SystemConfig
from core.config.registry import ConfigRegistry


class ConfigService:
    """Service to load and orchestrate system configurations."""

    def __init__(self) -> None:
        self._cache: Optional[SystemConfig] = None
        self._yaml_parser = YAMLParser()
        self._json_parser = JSONParser()

    def get_parser(self, file_path: Path) -> BaseParser:
        """Get the appropriate parser based on file extension."""
        ext = file_path.suffix.lower()
        if ext in (".yaml", ".yml"):
            return self._yaml_parser
        elif ext == ".json":
            return self._json_parser
        else:
            raise ConfigError(f"Unsupported configuration file extension: {ext}")

    def load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a single configuration file into a dictionary."""
        parser = self.get_parser(file_path)
        data = parser.parse(file_path)
        return EnvResolver.resolve(data)

    def load_from_dir(self, config_dir: Path, reload: bool = False) -> SystemConfig:
        """
        Load all configuration files from a directory and build SystemConfig.

        Args:
            config_dir: Path to the directory containing configuration files.
            reload: If True, bypass the cache and reload from disk.

        Returns:
            A frozen SystemConfig instance.
        """
        if self._cache is not None and not reload:
            return self._cache

        if not config_dir.exists():
            print(f"[ConfigService] Warning: Config directory not found: {config_dir}")
            return SystemConfig()

        merged_data: Dict[str, Any] = {}

        # 1. Parse & Resolve
        for file_path in sorted(config_dir.glob("*.yaml")):
            name = file_path.stem
            parsed = self.load_file(file_path)
            
            # Since SystemConfig.from_dict expects a flat dictionary of sub-configs,
            # or sub-configs nested under their own names:
            # (e.g. data["app"] = {...})
            # Most of our yaml files wrap everything under the key of the file name (e.g. `app: { ... }`)
            # If so, we can just extract that inner key.
            # E.g., if app.yaml has `app: {name: "Eric"}`, we pull `data["app"]`.
            if name in parsed:
                merged_data[name] = parsed[name]
            else:
                merged_data[name] = parsed

        # 2. Schema Builder
        # SystemConfig handles mapping the top-level keys to its nested dataclass attributes
        try:
            config = SystemConfig.from_dict(merged_data)
        except Exception as e:
            raise ConfigError(f"Error building SystemConfig schemas: {e}")

        # 3. Validate
        try:
            config.validate()
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Error validating configurations: {e}")

        # 4. Cache
        self._cache = config

        return self._cache


# Alias for backward compatibility / facade naming preference
ConfigLoader = ConfigService
