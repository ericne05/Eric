"""
Configuration Schema Registry.

Provides a dynamic registry to map configuration keys (e.g., 'app') to their
corresponding @dataclass schemas (e.g., AppConfig). This allows plugins or
other modules to register their own configuration schemas dynamically without
modifying the core loader.
"""

from typing import Type, Dict

from core.config.exceptions import UnknownSchemaError


class ConfigRegistry:
    """Registry mapping string keys to configuration schema classes."""
    
    _registry: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str, schema_cls: Type) -> None:
        """
        Register a new configuration schema.

        Args:
            name: The key used in the system config (e.g., 'app').
            schema_cls: The dataclass schema type.
        """
        cls._registry[name] = schema_cls

    @classmethod
    def get(cls, name: str) -> Type:
        """
        Get the schema class for a given configuration key.

        Args:
            name: The key to look up.

        Returns:
            The registered schema class.

        Raises:
            UnknownSchemaError: If the key is not registered.
        """
        if name not in cls._registry:
            raise UnknownSchemaError(f"No schema registered for config key: '{name}'")
        return cls._registry[name]

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a schema is registered for the given key."""
        return name in cls._registry

    @classmethod
    def clear(cls) -> None:
        """Clear all registered schemas (useful for testing)."""
        cls._registry.clear()
