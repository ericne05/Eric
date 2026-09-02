"""
Desktop Runtime Enums.
"""

from enum import Enum


class DesktopState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class DesktopPermissions(str, Enum):
    MOUSE_CLICK = "mouse_click"
    KEYBOARD_INPUT = "keyboard_input"
    WINDOW_MANAGE = "window_manage"
    SCREENSHOT = "screenshot"
    SYSTEM_CONTROL = "system_control"
    CLIPBOARD = "clipboard"
    NOTIFICATION = "notification"


class WindowSelectorType(str, Enum):
    TITLE = "title"
    CLASS_NAME = "class_name"
    PROCESS_ID = "process_id"
    HANDLE = "handle"
    AI_FALLBACK = "ai_fallback"


class DesktopActionType(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    FOCUS_WINDOW = "focus_window"
    DRAG = "drag"
    SYSTEM_POWER = "system_power"


class ActionPolicy(str, Enum):
    CONTINUE = "continue"
    ABORT = "abort"
    RETRY = "retry"
    IGNORE = "ignore"
    ASK_USER = "ask_user"
    RECOVER = "recover"


class RecoveryLevel(str, Enum):
    LOW = "low"          # Retry automatically
    MEDIUM = "medium"    # Alternative fallback action
    HIGH = "high"        # Request human intervention (AskUser)
    CRITICAL = "critical" # Emergency Stop


class RetryStrategyType(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class AdapterHealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
