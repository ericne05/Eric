"""
Vision Subsystem Package — Sprint 13.
"""

from core.vision.adapters.local_adapter import LocalVisionAdapter
from core.vision.adapters.mock_adapter import MockOCREngine, MockObjectDetector, MockScreenUnderstander, MockVisionAdapter
from core.vision.enums import GraphEdgeType, GraphNodeType, OCRMode, VisualElementType, VisionState
from core.vision.interfaces import IObjectDetector, IOCREngine, IScreenUnderstander, IVisionRuntime
from core.vision.managers.screen_parser import ScreenParser
from core.vision.models import (
    BoundingBox,
    DetectedElement,
    GraphEdge,
    GraphNode,
    OCRResult,
    OCRTextBlock,
    SemanticScreenGraph,
    VisionIntelligenceLayer,
    VisionObservation,
)
from core.vision.planner import ClickTarget, VisualPlanner

__all__ = [
    # Enums
    "VisionState", "OCRMode", "VisualElementType", "GraphNodeType", "GraphEdgeType",
    # Models
    "BoundingBox", "DetectedElement", "OCRTextBlock", "OCRResult",
    "GraphNode", "GraphEdge", "SemanticScreenGraph",
    "VisionObservation", "VisionIntelligenceLayer",
    # Interfaces
    "IOCREngine", "IObjectDetector", "IScreenUnderstander", "IVisionRuntime",
    # Adapters
    "MockOCREngine", "MockObjectDetector", "MockScreenUnderstander", "MockVisionAdapter",
    "LocalVisionAdapter",
    # Managers
    "ScreenParser",
    # Planner
    "VisualPlanner", "ClickTarget",
]
