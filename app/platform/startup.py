"""
Windows Autostart / Login Management (app/platform/startup.py).

Provides:
- WindowsStartupManager: Configures HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
- MockStartupManager: In-memory mock ensuring tests NEVER mutate the real Windows registry.
"""

import logging
import os
import sys
from typing import Optional

from app.platform.interfaces import IStartupManager

logger = logging.getLogger(__name__)

REG_KEY_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_APP_NAME = "EricDesktopAssistant"


class WindowsStartupManager(IStartupManager):
    """
    Manages Windows autostart on user logon via the CurrentVersion\\Run registry key.

    Strictly disabled by default during development and tests to prevent unintended registry changes.
    """

    def __init__(self, executable_path: Optional[str] = None):
        self._executable_path = executable_path or sys.executable

    def is_enabled(self) -> bool:
        if sys.platform != "win32":
            return False

        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_RUN, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, REG_APP_NAME)
                return True
        except (FileNotFoundError, OSError):
            return False
        except Exception as e:
            logger.warning(f"[WindowsStartupManager] Error querying startup registry: {e}")
            return False

    def enable(self) -> None:
        if sys.platform != "win32":
            logger.debug("[WindowsStartupManager] Non-Windows OS; cannot enable registry autostart.")
            return

        try:
            import winreg
            # Support both frozen PyInstaller executable and dev script
            command = f'"{self._executable_path}"'
            if not getattr(sys, "frozen", False):
                # When running from source, launch main.py
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
                command = f'"{self._executable_path}" "{main_py}"'

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_RUN, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, REG_APP_NAME, 0, winreg.REG_SZ, command)
            logger.info(f"[WindowsStartupManager] Enabled autostart with command: {command}")
        except Exception as e:
            logger.error(f"[WindowsStartupManager] Failed to enable autostart: {e}", exc_info=True)
            raise

    def disable(self) -> None:
        if sys.platform != "win32":
            return

        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_RUN, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, REG_APP_NAME)
            logger.info("[WindowsStartupManager] Disabled autostart.")
        except FileNotFoundError:
            pass  # Already disabled
        except Exception as e:
            logger.warning(f"[WindowsStartupManager] Error disabling autostart: {e}")


class MockStartupManager(IStartupManager):
    """
    In-memory mock for unit tests, ensuring zero registry touches.
    """

    def __init__(self, initially_enabled: bool = False):
        self._enabled: bool = initially_enabled
        self.enable_call_count: int = 0
        self.disable_call_count: int = 0

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self.enable_call_count += 1
        self._enabled = True

    def disable(self) -> None:
        self.disable_call_count += 1
        self._enabled = False
