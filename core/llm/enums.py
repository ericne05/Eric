"""
LLM Subsystem Enums.
"""

from enum import Enum


class MessageRole(str, Enum):
    """
    Role of the sender of an LLM message.
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(str, Enum):
    """
    Reason why the LLM generation stopped.
    """
    STOP = "stop"
    TOOL_CALLS = "tool_calls"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TIMEOUT = "timeout"
    ERROR = "error"
