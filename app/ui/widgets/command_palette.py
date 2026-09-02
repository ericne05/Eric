"""
Command Palette Component.
Ctrl+Shift+P Quick Command Palette widget for instant app actions.
"""

from typing import Callable, Dict, List, Optional


class CommandPalette:
    """
    Ctrl+Shift+P Quick Action Command Palette.
    """

    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        self.register_command("Open Settings", lambda: "Opened Settings")
        self.register_command("Restart Runtime", lambda: "Runtimes Restarted")
        self.register_command("Reload Plugins", lambda: "Plugins Reloaded")
        self.register_command("Clear Memory", lambda: "Memory Cleared")
        self.register_command("Health Check", lambda: "Health Check OK")

    def register_command(self, name: str, callback: Callable) -> None:
        self._commands[name] = callback

    def search(self, query: str) -> List[str]:
        query_lower = query.lower()
        return [cmd for cmd in self._commands.keys() if query_lower in cmd.lower()]

    def execute_command(self, name: str) -> Optional[str]:
        cb = self._commands.get(name)
        if cb:
            return cb()
        return None
