"""
Vision Runtime Interfaces.

Every OCR engine, object detector, and screen understander plugs in
through these interfaces. Swapping Tesseract → EasyOCR → PaddleOCR
or Tesseract → VLM never touches the Planner or upper layers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.browser.enums import WorkflowState
from core.runtime.interfaces import IRuntime, IRuntimeCapability
from core.vision.models import (
    BoundingBox,
    DetectedElement,
    OCRResult,
    SemanticScreenGraph,
    VisionObservation,
)


class IOCREngine(ABC):
    """
    Interface for any OCR implementation.
    Implementations: TesseractOCR, EasyOCR, PaddleOCR, MockOCR, VLMCloud
    """

    @abstractmethod
    async def extract_text(self, image_base64: str) -> OCRResult:
        """Extract all text from a base64-encoded image."""
        pass

    @abstractmethod
    async def find_text_bounds(self, image_base64: str, query_text: str) -> List[BoundingBox]:
        """
        Locate the bounding boxes of a specific text string within the image.
        Returns empty list if not found.
        """
        pass


class IObjectDetector(ABC):
    """
    Interface for any UI element detection implementation.
    Implementations: MockDetector, YOLOv8UIDetector, VLMDetector
    """

    @abstractmethod
    async def detect_elements(self, image_base64: str) -> List[DetectedElement]:
        """
        Detect UI elements (buttons, inputs, icons, checkboxes, etc.)
        in a base64-encoded screenshot and return their locations.
        """
        pass


class IScreenUnderstander(ABC):
    """
    Interface for holistic screen understanding.
    Takes raw OCR and detected elements, emits a SemanticScreenGraph.
    Implementations: RuleBasedUnderstander, VLMUnderstander
    """

    @abstractmethod
    async def build_graph(
        self,
        image_base64: str,
        ocr_result: OCRResult,
        detected_elements: List[DetectedElement],
    ) -> SemanticScreenGraph:
        """
        Combine OCR text blocks and detected elements into a
        Semantic Screen Graph that the Planner can reason over.
        """
        pass


class IVisionRuntime(IRuntime, ABC):
    """
    Unified Vision Runtime interface.

    Inherits the full IRuntime lifecycle (start → observe → plan → execute
    → recover → shutdown) and adds Vision-specific accessors.
    """

    @property
    @abstractmethod
    def ocr_engine(self) -> IOCREngine:
        pass

    @property
    @abstractmethod
    def object_detector(self) -> IObjectDetector:
        pass

    @property
    @abstractmethod
    def screen_understander(self) -> IScreenUnderstander:
        pass

    @abstractmethod
    async def analyze_screenshot(self, image_base64: str) -> VisionObservation:
        """
        Full pipeline: OCR + detect + understand → VisionObservation
        containing the populated SemanticScreenGraph.
        """
        pass
