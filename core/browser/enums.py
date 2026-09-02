"""
Browser Runtime Enums.
"""

from enum import Enum


class BrowserState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    CLOSED = "closed"


class BrowserPermissions(str, Enum):
    READ_PAGE = "read_page"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    COOKIES = "cookies"
    CLIPBOARD = "clipboard"
    GEOLOCATION = "geolocation"
    CAMERA = "camera"
    MICROPHONE = "microphone"


class WorkflowState(str, Enum):
    INIT = "init"
    OBSERVING = "observing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    SUCCESS = "success"
    FAILED = "failed"
    RECOVERING = "recovering"


class SelectorType(str, Enum):
    ROLE = "role"
    TEXT = "text"
    CSS = "css"
    XPATH = "xpath"
    AI_FALLBACK = "ai_fallback"
