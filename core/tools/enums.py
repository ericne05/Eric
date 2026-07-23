"""
Tool System Enums.
"""

from enum import Enum


class ToolPermission(str, Enum):
    """
    Permissions that a Tool can request.
    """
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    WINDOW = "window"
    PROCESS = "process"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    SYSTEM = "system"
    MEMORY = "memory"


class ToolStatus(str, Enum):
    """
    Execution status of a Tool.
    """
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    CANCELLED = "cancelled"
