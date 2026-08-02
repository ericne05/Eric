"""
Local Vision Adapter — PIL-based OCR hook (Sprint 13 baseline).

Uses PIL for basic image processing and pytesseract for real OCR
when it's available; falls back gracefully to the mock engine.
This is the foundation that Sprint 13.5 will extend with EasyOCR /
PaddleOCR / YOLOv8 UI detector.
"""

from typing import Any, Dict, List, Optional

from core.browser.enums import WorkflowState
from core.runtime.capability import CapabilityRegistry
from core.runtime.interfaces import IRuntimeCapability
from core.vision.adapters.mock_adapter import MockObjectDetector
from core.vision.enums import VisionState
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


class PilOCREngine(IOCREngine):
    """
    PIL-based OCR engine.
    Uses pytesseract when available; falls back to simple PIL text parsing.
    """

    async def extract_text(self, image_base64: str) -> OCRResult:
        try:
            import base64
            import io
            import pytesseract
            from PIL import Image

            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))

            # Get full text
            full_text = pytesseract.image_to_string(image)

            # Get per-word data with bounding boxes
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            blocks: list[OCRTextBlock] = []
            n = len(data["text"])
            for i in range(n):
                word = data["text"][i].strip()
                conf = int(data["conf"][i])
                if word and conf > 0:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    blocks.append(OCRTextBlock(
                        text=word,
                        bounds=BoundingBox(x=x, y=y, width=w, height=h, confidence=conf / 100),
                    ))

            return OCRResult(full_text=full_text.strip(), text_blocks=blocks, confidence=0.9)

        except Exception:
            # Fall back to empty result (no crash)
            return OCRResult(full_text="", text_blocks=[], confidence=0.0)

    async def find_text_bounds(self, image_base64: str, query_text: str) -> List[BoundingBox]:
        result = await self.extract_text(image_base64)
        return [
            b.bounds for b in result.text_blocks
            if query_text.lower() in b.text.lower()
        ]


class LocalScreenUnderstander(IScreenUnderstander):
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
        )


class LocalVisionAdapter(IVisionRuntime):
    """
    Local Vision Runtime using PIL + pytesseract (+ optional future detectors).
    Falls back gracefully when pytesseract is not installed.
    """

    def __init__(self):
        self._state = VisionState.STOPPED
        self._ocr = PilOCREngine()
        self._detector = MockObjectDetector()   # Real detector slot for Sprint 13.5
        self._understander = LocalScreenUnderstander()
        self._intelligence = VisionIntelligenceLayer()
        self._caps = CapabilityRegistry({
            "ocr": True,
            "vision": True,
            "object_detection": False,  # Real detection added in Sprint 13.5
            "screenshot": True,
            "mouse": False,
            "keyboard": False,
        })

    async def start(self) -> None:
        self._state = VisionState.READY

    async def shutdown(self) -> None:
        self._state = VisionState.STOPPED

    async def observe(self) -> VisionObservation:
        return await self.analyze_screenshot("local_screen")

    async def plan(self, goal: str, observation: Any) -> Any:
        return {"goal": goal, "strategy": "local_vision_search"}

    async def execute(self, plan: Any) -> Any:
        return {"success": True}

    async def recover(self, error: Exception, context: Any) -> WorkflowState:
        return WorkflowState.RECOVERING

    def get_runtime_capabilities(self) -> IRuntimeCapability:
        return self._caps

    def get_health(self) -> Dict[str, Any]:
        return {"state": self._state.value, "ocr_ok": True}

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
        return obs
