"""
Custom exceptions for the Configuration System.
"""

class ConfigError(Exception):
    """Base exception for all configuration errors."""
    pass


class MissingConfigError(ConfigError):
    """Raised when a required configuration value or file is missing."""
    pass


class SchemaValidationError(ConfigError):
    """Raised when a configuration fails schema validation."""
    pass


class InvalidEnvironmentVariableError(ConfigError):
    """Raised when an environment variable placeholder cannot be resolved or is malformed."""
    pass


class UnknownSchemaError(ConfigError):
    """Raised when a configuration key does not map to a registered schema."""
    pass
