"""
Environment Variable Resolver.

Resolves `${VAR}` and `${VAR:default}` placeholders in configuration values.
"""

import os
import re
from typing import Any

from core.config.exceptions import InvalidEnvironmentVariableError


class EnvResolver:
    """Resolves environment variable placeholders in configuration objects."""

    # Matches ${VAR} or ${VAR:default}
    _ENV_PATTERN = re.compile(r"^\$\{([a-zA-Z0-9_]+)(?::([^}]*))?\}$")

    @classmethod
    def resolve(cls, obj: Any) -> Any:
        """
        Recursively resolve environment variables in a dictionary, list, or string.

        Args:
            obj: The object to resolve (dict, list, string, etc.).

        Returns:
            The resolved object.
        """
        if isinstance(obj, dict):
            return {k: cls.resolve(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls.resolve(item) for item in obj]
        if isinstance(obj, str):
            return cls._resolve_string(obj)
        return obj

    @classmethod
    def _resolve_string(cls, value: str) -> Any:
        """Resolve a single string if it matches the exact placeholder pattern."""
        match = cls._ENV_PATTERN.match(value)
        if match:
            env_var = match.group(1)
            default_val = match.group(2)  # Could be None if no default specified

            # Look up environment variable
            env_val = os.environ.get(env_var)

            if env_val is not None:
                return env_val
            
            if default_val is not None:
                return default_val
            
            # If no env var and no default, keep the placeholder or raise error.
            # Keeping placeholder is backward-compatible with original bootstrap logic,
            # but raising might be strictly safer. For now, keep the placeholder.
            return value

        return value
