"""
Vision Runtime Enums.
"""

from enum import Enum


class VisionState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class OCRMode(str, Enum):
    FAST = "fast"        # Local lightweight (Tesseract / EasyOCR / PIL heuristic)
    ACCURATE = "accurate"  # VLM / Cloud API for complex layouts


class VisualElementType(str, Enum):
    TEXT = "text"
    BUTTON = "button"
    INPUT = "input"
    ICON = "icon"
    IMAGE = "image"
    CHECKBOX = "checkbox"
    LINK = "link"
    MENU = "menu"
    UNKNOWN = "unknown"


class GraphNodeType(str, Enum):
    """Node types in the Semantic Screen Graph."""
    REGION = "region"       # A spatial group of elements
    ELEMENT = "element"     # A single UI element
    TEXT_BLOCK = "text_block"  # A block of readable text


class GraphEdgeType(str, Enum):
    """Relationship types between nodes in the Semantic Screen Graph."""
    CONTAINS = "contains"   # Parent → Child containment
    NEAR = "near"           # Spatial proximity
    LABEL_OF = "label_of"   # Text label describes adjacent element
    FOLLOWS = "follows"     # Sequential reading order
