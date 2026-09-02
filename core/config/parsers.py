"""
Configuration Parsers.

Defines the interface and implementations for parsing various configuration
file formats (YAML, JSON).
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

import yaml

from core.config.exceptions import ConfigError


class BaseParser(ABC):
    """Abstract base class for configuration parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a configuration file into a dictionary.

        Args:
            file_path: Path to the configuration file.

        Returns:
            Dictionary containing parsed configuration data.

        Raises:
            ConfigError: If parsing fails.
        """
        pass


class YAMLParser(BaseParser):
    """Parser for YAML (.yaml, .yml) configuration files."""

    def parse(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise ConfigError(f"YAML file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Error parsing YAML {file_path.name}: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading {file_path.name}: {e}")


class JSONParser(BaseParser):
    """Parser for JSON (.json) configuration files."""

    def parse(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise ConfigError(f"JSON file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            raise ConfigError(f"Error parsing JSON {file_path.name}: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading {file_path.name}: {e}")
