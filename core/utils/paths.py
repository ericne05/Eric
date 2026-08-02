"""
Application Path Utilities for Commercial Windows Desktop Packaging.
Handles User Data Isolation in %LOCALAPPDATA%\\Eric (logs, memory, cache, sessions, settings).
"""

import os, sys


def get_app_data_dir() -> str:
    """Returns the persistent User Data directory under %LOCALAPPDATA%\\Eric."""
    if sys.platform == "win32":
        base_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    else:
        base_dir = os.path.expanduser("~/.config")

    app_data = os.path.join(base_dir, "Eric")
    os.makedirs(app_data, exist_ok=True)
    os.makedirs(os.path.join(app_data, "memory"), exist_ok=True)
    os.makedirs(os.path.join(app_data, "logs"), exist_ok=True)
    os.makedirs(os.path.join(app_data, "cache"), exist_ok=True)
    os.makedirs(os.path.join(app_data, "sessions"), exist_ok=True)
    return app_data


def get_resource_path(relative_path: str) -> str:
    """Returns absolute path to resource, working for dev and PyInstaller single-file bundle."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)
