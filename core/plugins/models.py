"""
Plugin System Models.

Defines the PluginManifest dataclass parsed from plugin.yaml.
"""

from dataclasses import dataclass, field

from core.plugins.exceptions import PluginManifestError


@dataclass(frozen=True)
class PluginManifest:
    """
    Metadata and configuration parsed from a plugin's plugin.yaml manifest.

    Attributes:
        name: Unique string identifier for the plugin.
        version: Semantic version string.
        api_version: Integer representing Eric API compatibility.
        author: Author name or organization.
        description: Brief description of the plugin's purpose.
        entry: Python import path to the plugin class (e.g., 'browser.main:BrowserPlugin').
        priority: Loading priority (lower number = loaded earlier). Default 100.
        enabled: Whether the plugin should be loaded at all. Default True.
        dependencies: List of plugin names this plugin requires.
        permissions: List of permissions requested by this plugin.
        plugin_dir: Absolute path to the plugin's root directory (injected by loader).
    """

    name: str
    version: str
    entry: str
    api_version: int = 1
    author: str = "Unknown"
    description: str = ""
    priority: int = 100
    enabled: bool = True
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    plugin_dir: str = ""

    @classmethod
    def from_dict(cls, data: dict, plugin_dir: str = "") -> "PluginManifest":
        """
        Create a PluginManifest from a dictionary (typically parsed YAML).

        Raises:
            PluginManifestError: If required fields are missing.
        """
        required_fields = ["name", "version", "entry"]
        for field_name in required_fields:
            if field_name not in data:
                raise PluginManifestError(f"Manifest missing required field: '{field_name}'")

        return cls(
            name=data["name"],
            version=str(data["version"]),
            entry=data["entry"],
            api_version=int(data.get("api_version", 1)),
            author=data.get("author", "Unknown"),
            description=data.get("description", ""),
            priority=int(data.get("priority", 100)),
            enabled=bool(data.get("enabled", True)),
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            plugin_dir=plugin_dir,
        )
