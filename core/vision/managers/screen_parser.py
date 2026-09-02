"""
SemanticScreenGraph Builder — Screen Parser.

Takes raw OCR results and detected elements and wires them into
a meaningful graph of spatial and semantic relationships.
"""

from core.vision.enums import GraphEdgeType, GraphNodeType, VisualElementType
from core.vision.models import (
    BoundingBox,
    DetectedElement,
    GraphEdge,
    GraphNode,
    OCRResult,
    SemanticScreenGraph,
)

# Pixel distance threshold for "near" edges
_NEAR_THRESHOLD_PX = 150
# Pixel distance threshold for "label_of" edges
_LABEL_THRESHOLD_PX = 80


class ScreenParser:
    """
    Builds a SemanticScreenGraph from raw OCR + detected elements.

    Algorithm:
      1. Create a GraphNode for every OCR text block.
      2. Create a GraphNode for every detected UI element.
      3. Wire CONTAINS edges (text block whose bounds overlap an element).
      4. Wire NEAR edges (nodes within _NEAR_THRESHOLD_PX of each other).
      5. Wire LABEL_OF edges (small text node close to an interactive element).
      6. Wire FOLLOWS edges (text blocks in reading order: top-to-bottom, left-to-right).
    """

    def build(
        self,
        ocr_result: OCRResult,
        detected_elements: list[DetectedElement],
        screenshot_base64: str | None = None,
        screen_resolution: tuple[int, int] = (1920, 1080),
    ) -> SemanticScreenGraph:
        graph = SemanticScreenGraph(
            screenshot_base64=screenshot_base64,
            screen_resolution=screen_resolution,
        )

        # Step 1: OCR text blocks → TEXT_BLOCK nodes
        text_nodes: list[GraphNode] = []
        for block in ocr_result.text_blocks:
            node = GraphNode(
                id=block.id,
                node_type=GraphNodeType.TEXT_BLOCK,
                label=block.text[:60],
                bounds=block.bounds,
                text_block=block,
            )
            graph.add_node(node)
            text_nodes.append(node)

        # Step 2: Detected elements → ELEMENT nodes
        element_nodes: list[GraphNode] = []
        for elem in detected_elements:
            node = GraphNode(
                id=elem.id,
                node_type=GraphNodeType.ELEMENT,
                label=elem.label or elem.text or elem.element_type.value,
                bounds=elem.bounds,
                element=elem,
            )
            graph.add_node(node)
            element_nodes.append(node)

        all_nodes = text_nodes + element_nodes

        # Step 3: CONTAINS — text block whose bounds overlap an element
        for txt_node in text_nodes:
            if not txt_node.bounds:
                continue
            for elem_node in element_nodes:
                if not elem_node.bounds:
                    continue
                if txt_node.bounds.overlaps(elem_node.bounds):
                    graph.add_edge(elem_node.id, txt_node.id, GraphEdgeType.CONTAINS)

        # Step 4 & 5: NEAR + LABEL_OF
        for i, node_a in enumerate(all_nodes):
            for node_b in all_nodes[i + 1:]:
                if not node_a.bounds or not node_b.bounds:
                    continue
                dist = node_a.bounds.distance_to(node_b.bounds)

                if dist <= _NEAR_THRESHOLD_PX:
                    graph.add_edge(node_a.id, node_b.id, GraphEdgeType.NEAR, weight=1.0 - dist / _NEAR_THRESHOLD_PX)

                if dist <= _LABEL_THRESHOLD_PX:
                    # If one is a text block and the other is an interactive element
                    if (
                        node_a.node_type == GraphNodeType.TEXT_BLOCK
                        and node_b.node_type == GraphNodeType.ELEMENT
                        and node_b.element
                        and node_b.element.is_interactive
                    ):
                        graph.add_edge(node_a.id, node_b.id, GraphEdgeType.LABEL_OF)
                    elif (
                        node_b.node_type == GraphNodeType.TEXT_BLOCK
                        and node_a.node_type == GraphNodeType.ELEMENT
                        and node_a.element
                        and node_a.element.is_interactive
                    ):
                        graph.add_edge(node_b.id, node_a.id, GraphEdgeType.LABEL_OF)

        # Step 6: FOLLOWS — reading order for text blocks (top → bottom, left → right)
        sorted_text = sorted(
            [n for n in text_nodes if n.bounds],
            key=lambda n: (n.bounds.y, n.bounds.x),
        )
        for i in range(len(sorted_text) - 1):
            graph.add_edge(sorted_text[i].id, sorted_text[i + 1].id, GraphEdgeType.FOLLOWS)

        return graph
