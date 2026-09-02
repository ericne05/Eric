"""
Unit Tests — Sprint 13: Vision Runtime.
"""

import pytest

from core.vision import (
    BoundingBox,
    ClickTarget,
    DetectedElement,
    GraphEdgeType,
    GraphNode,
    GraphNodeType,
    MockVisionAdapter,
    OCRResult,
    OCRTextBlock,
    ScreenParser,
    SemanticScreenGraph,
    VisualElementType,
    VisualPlanner,
)


# ── BoundingBox geometry ─────────────────────────────────────────────────

class TestBoundingBox:
    def test_center(self):
        box = BoundingBox(x=100, y=200, width=60, height=40)
        assert box.center_x == 130
        assert box.center_y == 220

    def test_overlaps_true(self):
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=50, y=50, width=100, height=100)
        assert a.overlaps(b) is True

    def test_overlaps_false(self):
        a = BoundingBox(x=0, y=0, width=50, height=50)
        b = BoundingBox(x=100, y=100, width=50, height=50)
        assert a.overlaps(b) is False

    def test_distance(self):
        a = BoundingBox(x=0, y=0, width=0, height=0)
        b = BoundingBox(x=3, y=4, width=0, height=0)
        assert a.distance_to(b) == pytest.approx(5.0)


# ── SemanticScreenGraph ───────────────────────────────────────────────────

class TestSemanticScreenGraph:
    def _make_graph(self) -> SemanticScreenGraph:
        graph = SemanticScreenGraph()
        submit_node = GraphNode(
            id="n1",
            node_type=GraphNodeType.ELEMENT,
            label="Submit Button",
            bounds=BoundingBox(x=200, y=270, width=80, height=36),
        )
        username_text = GraphNode(
            id="n2",
            node_type=GraphNodeType.TEXT_BLOCK,
            label="Username",
            bounds=BoundingBox(x=100, y=120, width=80, height=18),
        )
        graph.add_node(submit_node)
        graph.add_node(username_text)
        graph.add_edge("n1", "n2", GraphEdgeType.NEAR)
        return graph

    def test_add_and_find_by_label(self):
        graph = self._make_graph()
        result = graph.find_by_label("Submit")
        assert result is not None
        assert "Submit" in result.label

    def test_find_by_label_not_found(self):
        graph = self._make_graph()
        assert graph.find_by_label("Nonexistent") is None

    def test_find_by_text(self):
        graph = SemanticScreenGraph()
        block = OCRTextBlock(text="Login to continue", bounds=BoundingBox())
        node = GraphNode(id="t1", node_type=GraphNodeType.TEXT_BLOCK, label="Login", text_block=block)
        graph.add_node(node)
        results = graph.find_by_text("Login")
        assert len(results) == 1

    def test_node_and_edge_count(self):
        graph = self._make_graph()
        assert graph.node_count == 2
        assert graph.edge_count == 1

    def test_get_neighbours(self):
        graph = self._make_graph()
        neighbours = graph.get_neighbours("n1")
        assert any(n.id == "n2" for n in neighbours)


# ── ScreenParser — graph building ────────────────────────────────────────

class TestScreenParser:
    def _make_ocr(self) -> OCRResult:
        return OCRResult(
            full_text="Username Password Submit Cancel",
            text_blocks=[
                OCRTextBlock(text="Username", bounds=BoundingBox(x=100, y=120, width=80, height=18)),
                OCRTextBlock(text="Password", bounds=BoundingBox(x=100, y=200, width=80, height=18)),
                OCRTextBlock(text="Submit", bounds=BoundingBox(x=200, y=280, width=60, height=20)),
                OCRTextBlock(text="Cancel", bounds=BoundingBox(x=300, y=280, width=60, height=20)),
            ],
        )

    def _make_elements(self) -> list[DetectedElement]:
        return [
            DetectedElement(
                id="btn-submit",
                element_type=VisualElementType.BUTTON,
                label="Submit Button",
                bounds=BoundingBox(x=200, y=270, width=80, height=36),
                is_interactive=True,
            ),
            DetectedElement(
                id="inp-username",
                element_type=VisualElementType.INPUT,
                label="Username Input",
                bounds=BoundingBox(x=100, y=140, width=200, height=30),
                is_interactive=True,
            ),
        ]

    def test_builds_graph_with_nodes(self):
        parser = ScreenParser()
        graph = parser.build(self._make_ocr(), self._make_elements())
        # 4 text blocks + 2 elements = 6 nodes
        assert graph.node_count == 6

    def test_follows_edges_in_reading_order(self):
        parser = ScreenParser()
        graph = parser.build(self._make_ocr(), [])
        follows_edges = [e for e in graph.edges if e.edge_type == GraphEdgeType.FOLLOWS]
        # 4 text blocks → 3 FOLLOWS edges
        assert len(follows_edges) == 3

    def test_near_edges_created(self):
        parser = ScreenParser()
        graph = parser.build(self._make_ocr(), self._make_elements())
        near_edges = [e for e in graph.edges if e.edge_type == GraphEdgeType.NEAR]
        assert len(near_edges) > 0

    def test_contains_edge_when_text_overlaps_element(self):
        parser = ScreenParser()
        ocr = OCRResult(
            full_text="Submit",
            text_blocks=[
                OCRTextBlock(text="Submit", bounds=BoundingBox(x=210, y=278, width=50, height=18)),
            ],
        )
        elements = [
            DetectedElement(
                id="btn",
                element_type=VisualElementType.BUTTON,
                label="Submit Button",
                bounds=BoundingBox(x=200, y=270, width=80, height=36),
                is_interactive=True,
            )
        ]
        graph = parser.build(ocr, elements)
        contains_edges = [e for e in graph.edges if e.edge_type == GraphEdgeType.CONTAINS]
        assert len(contains_edges) == 1


# ── VisualPlanner ─────────────────────────────────────────────────────────

class TestVisualPlanner:
    def _make_graph_with_submit(self) -> SemanticScreenGraph:
        parser = ScreenParser()
        ocr = OCRResult(
            full_text="Submit",
            text_blocks=[
                OCRTextBlock(text="Submit", bounds=BoundingBox(x=210, y=278, width=50, height=18)),
            ],
        )
        elements = [
            DetectedElement(
                id="btn-submit",
                element_type=VisualElementType.BUTTON,
                label="Submit Button",
                bounds=BoundingBox(x=200, y=270, width=80, height=36),
                is_interactive=True,
            )
        ]
        return parser.build(ocr, elements, screenshot_base64="fake")

    def test_find_click_target_by_label(self):
        planner = VisualPlanner()
        graph = self._make_graph_with_submit()
        target = planner.find_click_target(graph, "Submit")
        assert target is not None
        assert isinstance(target, ClickTarget)
        assert target.confidence > 0.5

    def test_find_click_target_returns_none_for_unknown(self):
        planner = VisualPlanner()
        graph = SemanticScreenGraph()
        target = planner.find_click_target(graph, "DoesNotExist")
        assert target is None

    def test_extract_visible_text(self):
        planner = VisualPlanner()
        graph = self._make_graph_with_submit()
        text = planner.extract_visible_text(graph)
        assert "Submit" in text

    def test_get_element_at_coordinates(self):
        planner = VisualPlanner()
        graph = self._make_graph_with_submit()
        # Click inside the Submit button bounds
        node = planner.get_element_at(graph, x=230, y=285)
        assert node is not None

    def test_get_element_at_outside_all(self):
        planner = VisualPlanner()
        graph = self._make_graph_with_submit()
        node = planner.get_element_at(graph, x=5000, y=5000)
        assert node is None


# ── MockVisionAdapter full pipeline ──────────────────────────────────────

class TestMockVisionAdapter:
    @pytest.mark.asyncio
    async def test_lifecycle(self):
        adapter = MockVisionAdapter()
        await adapter.start()
        health = adapter.get_health()
        assert health["state"] == "ready"
        await adapter.shutdown()
        assert adapter.get_health()["state"] == "stopped"

    @pytest.mark.asyncio
    async def test_analyze_screenshot_returns_observation(self):
        adapter = MockVisionAdapter()
        await adapter.start()
        obs = await adapter.analyze_screenshot("fake_base64")
        assert obs.semantic_graph.node_count > 0
        assert obs.ocr_result.full_text != ""
        assert len(obs.detected_elements) > 0

    @pytest.mark.asyncio
    async def test_find_submit_button_via_planner(self):
        adapter = MockVisionAdapter()
        await adapter.start()
        obs = await adapter.analyze_screenshot("fake_base64")

        planner = VisualPlanner()
        target = planner.find_click_target(obs.semantic_graph, "Submit")
        assert target is not None
        assert target.x > 0 and target.y > 0

    def test_capabilities(self):
        adapter = MockVisionAdapter()
        caps = adapter.get_runtime_capabilities()
        assert caps.supports("ocr") is True
        assert caps.supports("vision") is True
        assert caps.supports("mouse") is False  # Vision doesn't control mouse directly

    @pytest.mark.asyncio
    async def test_capability_negotiator_integration(self):
        from core.runtime.capability import CapabilityNegotiator
        from core.desktop import MockDesktopAdapter
        from core.events.event_bus import EventBus

        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("vision", MockVisionAdapter())
        negotiator.register_runtime("desktop", MockDesktopAdapter(EventBus()))

        # Vision provides OCR; Desktop does not
        ocr_runtimes = negotiator.find_runtimes_supporting("ocr")
        assert "vision" in ocr_runtimes
        assert "desktop" not in ocr_runtimes

        # Desktop provides mouse; Vision does not
        mouse_runtimes = negotiator.find_runtimes_supporting("mouse")
        assert "desktop" in mouse_runtimes
        assert "vision" not in mouse_runtimes
