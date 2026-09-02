"""
Mock Vision Adapter — fast, offline, dependency-free.

Returns deterministic synthetic data that lets unit tests run in <0.1s
without loading Tesseract, EasyOCR, PyTorch or any ML model.
"""

from typing import Any, Dict, List, Optional

from core.browser.enums import WorkflowState
from core.runtime.capability import CapabilityRegistry
from core.runtime.interfaces import IRuntimeCapability
from core.vision.enums import VisionState, VisualElementType
from core.vision.interfaces import IObjectDetector, IOCREngine, IScreenUnderstander, IVisionRuntime
from core.vision.managers.screen_parser import ScreenParser
from core.vision.models import (
    BoundingBox,
    DetectedElement,
    OCRResult,
    OCRTextBlock,
    SemanticScreenGraph,
    VisionIntelligenceLayer,
    VisionObservation,
)


class MockOCREngine(IOCREngine):
    """Returns synthetic OCR text blocks for a fake 1920×1080 screen."""

    async def extract_text(self, image_base64: str) -> OCRResult:
        blocks = [
            OCRTextBlock(
                text="File  Edit  View  Help",
                bounds=BoundingBox(x=0, y=0, width=300, height=24, confidence=0.99),
            ),
            OCRTextBlock(
                text="Username",
                bounds=BoundingBox(x=100, y=120, width=80, height=18, confidence=0.95),
            ),
            OCRTextBlock(
                text="Password",
                bounds=BoundingBox(x=100, y=200, width=80, height=18, confidence=0.95),
            ),
            OCRTextBlock(
                text="Submit",
                bounds=BoundingBox(x=200, y=280, width=60, height=30, confidence=0.97),
            ),
            OCRTextBlock(
                text="Cancel",
                bounds=BoundingBox(x=300, y=280, width=60, height=30, confidence=0.97),
            ),
            OCRTextBlock(
                text="Error: Invalid credentials",
                bounds=BoundingBox(x=100, y=350, width=200, height=20, confidence=0.91),
            ),
        ]
        full_text = " ".join(b.text for b in blocks)
        return OCRResult(full_text=full_text, text_blocks=blocks, confidence=0.96)

    async def find_text_bounds(self, image_base64: str, query_text: str) -> List[BoundingBox]:
        result = await self.extract_text(image_base64)
        matches = [
            b.bounds for b in result.text_blocks
            if query_text.lower() in b.text.lower()
        ]
        return matches


class MockObjectDetector(IObjectDetector):
    """Returns synthetic UI elements for a fake login form."""

    async def detect_elements(self, image_base64: str) -> List[DetectedElement]:
        return [
            DetectedElement(
                id="elem-input-username",
                element_type=VisualElementType.INPUT,
                label="Username Input",
                text="",
                bounds=BoundingBox(x=100, y=140, width=200, height=30, confidence=0.92),
                is_interactive=True,
            ),
            DetectedElement(
                id="elem-input-password",
                element_type=VisualElementType.INPUT,
                label="Password Input",
                text="",
                bounds=BoundingBox(x=100, y=220, width=200, height=30, confidence=0.90),
                is_interactive=True,
            ),
            DetectedElement(
                id="elem-btn-submit",
                element_type=VisualElementType.BUTTON,
                label="Submit Button",
                text="Submit",
                bounds=BoundingBox(x=200, y=270, width=80, height=36, confidence=0.98),
                is_interactive=True,
            ),
            DetectedElement(
                id="elem-btn-cancel",
                element_type=VisualElementType.BUTTON,
                label="Cancel Button",
                text="Cancel",
                bounds=BoundingBox(x=300, y=270, width=80, height=36, confidence=0.96),
                is_interactive=True,
            ),
        ]


class MockScreenUnderstander(IScreenUnderstander):
    """Builds a SemanticScreenGraph using ScreenParser with mock data."""

    def __init__(self):
        self._parser = ScreenParser()

    async def build_graph(
        self,
        image_base64: str,
        ocr_result: OCRResult,
        detected_elements: List[DetectedElement],
    ) -> SemanticScreenGraph:
        return self._parser.build(
            ocr_result=ocr_result,
            detected_elements=detected_elements,
            screenshot_base64=image_base64,
            screen_resolution=(1920, 1080),
        )


class MockVisionAdapter(IVisionRuntime):
    """
    Full mock Vision Runtime implementing IVisionRuntime.
    Designed for unit/integration tests — no ML dependencies.
    Exposes can_ocr=True, can_vision=True to the CapabilityNegotiator.
    """

    def __init__(self):
        self._state = VisionState.STOPPED
        self._ocr = MockOCREngine()
        self._detector = MockObjectDetector()
        self._understander = MockScreenUnderstander()
        self._intelligence = VisionIntelligenceLayer()
        self._caps = CapabilityRegistry({
            "ocr": True,
            "vision": True,
            "object_detection": True,
            "screenshot": True,
            "mouse": False,
            "keyboard": False,
        })

    # ── IRuntime lifecycle ─────────────────────────────────────────────

    async def start(self) -> None:
        self._state = VisionState.READY

    async def shutdown(self) -> None:
        self._state = VisionState.STOPPED

    async def observe(self) -> VisionObservation:
        return await self.analyze_screenshot("mock_base64_screen")

    async def plan(self, goal: str, observation: Any) -> Any:
        return {"goal": goal, "strategy": "visual_search"}

    async def execute(self, plan: Any) -> Any:
        return {"success": True, "plan": plan}

    async def recover(self, error: Exception, context: Any) -> WorkflowState:
        return WorkflowState.RECOVERING

    def get_runtime_capabilities(self) -> IRuntimeCapability:
        return self._caps

    def get_health(self) -> Dict[str, Any]:
        return {"state": self._state.value, "ocr_ok": True, "detector_ok": True}

    # ── IVisionRuntime specifics ───────────────────────────────────────

    @property
    def ocr_engine(self) -> IOCREngine:
        return self._ocr

    @property
    def object_detector(self) -> IObjectDetector:
        return self._detector

    @property
    def screen_understander(self) -> IScreenUnderstander:
        return self._understander

    async def analyze_screenshot(self, image_base64: str) -> VisionObservation:
        """Full pipeline: OCR → detect → understand → VisionObservation."""
        ocr_result = await self._ocr.extract_text(image_base64)
        elements = await self._detector.detect_elements(image_base64)
        graph = await self._understander.build_graph(image_base64, ocr_result, elements)

        obs = VisionObservation(
            screenshot_base64=image_base64,
            ocr_result=ocr_result,
            detected_elements=elements,
            semantic_graph=graph,
        )
        self._intelligence.latest_observation = obs
        self._intelligence.graph_history.append(graph)
        return obs
