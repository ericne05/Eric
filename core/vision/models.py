"""
Vision Runtime Data Models.

The centrepiece is SemanticScreenGraph — the intermediate representation
that Planners use to reason about what's on screen, rather than raw
BoundingBox lists or OCR strings.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.vision.enums import GraphEdgeType, GraphNodeType, VisualElementType


# ── Primitive geometry ────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    """(x, y, width, height) in screen pixels with optional confidence score."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 1.0

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    @property
    def area(self) -> int:
        return self.width * self.height

    def overlaps(self, other: "BoundingBox") -> bool:
        """Returns True if this box overlaps with another."""
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )

    def distance_to(self, other: "BoundingBox") -> float:
        """Euclidean distance between centres."""
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return (dx * dx + dy * dy) ** 0.5


# ── Detected elements ────────────────────────────────────────────────────

@dataclass
class DetectedElement:
    """A single UI element located on screen."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    element_type: VisualElementType = VisualElementType.UNKNOWN
    label: str = ""
    text: str = ""
    bounds: BoundingBox = field(default_factory=BoundingBox)
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_interactive: bool = False


@dataclass
class OCRTextBlock:
    """A block of text extracted by an OCR engine."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    bounds: BoundingBox = field(default_factory=BoundingBox)
    language: str = "en"


@dataclass
class OCRResult:
    """Aggregated result from an OCR engine pass on an image."""
    full_text: str = ""
    text_blocks: List[OCRTextBlock] = field(default_factory=list)
    language: str = "en"
    confidence: float = 1.0


# ── Semantic Screen Graph ─────────────────────────────────────────────────

@dataclass
class GraphNode:
    """A node in the Semantic Screen Graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: GraphNodeType = GraphNodeType.ELEMENT
    label: str = ""
    bounds: Optional[BoundingBox] = None
    element: Optional[DetectedElement] = None
    text_block: Optional[OCRTextBlock] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A directed relationship between two nodes in the Semantic Screen Graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    edge_type: GraphEdgeType = GraphEdgeType.CONTAINS
    weight: float = 1.0


@dataclass
class SemanticScreenGraph:
    """
    The intermediate representation that the Planner uses to reason about the screen.

    Instead of raw BoundingBox lists or OCR strings, the Planner gets a graph
    where nodes are UI elements / text blocks / regions, and edges capture
    spatial and semantic relationships between them.

    Usage example:
        graph = SemanticScreenGraph(screenshot_base64="...")
        graph.add_node(GraphNode(label="Submit Button", element=...))
        target = graph.find_by_label("Submit")
        click_x, click_y = target.bounds.center_x, target.bounds.center_y
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    screenshot_base64: Optional[str] = None
    screen_resolution: Tuple[int, int] = (1920, 1080)
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, source_id: str, target_id: str, edge_type: GraphEdgeType, weight: float = 1.0) -> GraphEdge:
        edge = GraphEdge(source_id=source_id, target_id=target_id, edge_type=edge_type, weight=weight)
        self.edges.append(edge)
        return edge

    def find_by_label(self, label: str, partial: bool = True) -> Optional[GraphNode]:
        """Find the first node whose label matches (case-insensitive)."""
        label_lower = label.lower()
        for node in self.nodes.values():
            node_label = node.label.lower()
            if (partial and label_lower in node_label) or node_label == label_lower:
                return node
        return None

    def find_by_text(self, text: str, partial: bool = True) -> List[GraphNode]:
        """Find all nodes containing the given text."""
        text_lower = text.lower()
        results = []
        for node in self.nodes.values():
            node_text = ""
            if node.element:
                node_text = node.element.text.lower()
            elif node.text_block:
                node_text = node.text_block.text.lower()
            if (partial and text_lower in node_text) or node_text == text_lower:
                results.append(node)
        return results

    def get_interactive_elements(self) -> List[GraphNode]:
        """Return all nodes backed by interactive DetectedElements."""
        return [
            n for n in self.nodes.values()
            if n.element and n.element.is_interactive
        ]

    def get_neighbours(self, node_id: str) -> List[GraphNode]:
        """Return all nodes directly connected to the given node."""
        neighbour_ids = {
            e.target_id for e in self.edges if e.source_id == node_id
        } | {
            e.source_id for e in self.edges if e.target_id == node_id
        }
        return [self.nodes[nid] for nid in neighbour_ids if nid in self.nodes]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


# ── Vision observation & intelligence layer ───────────────────────────────

@dataclass
class VisionObservation:
    """Complete visual evidence for a single screen capture moment."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    screenshot_base64: Optional[str] = None
    screen_resolution: Tuple[int, int] = (1920, 1080)
    ocr_result: OCRResult = field(default_factory=OCRResult)
    detected_elements: List[DetectedElement] = field(default_factory=list)
    semantic_graph: SemanticScreenGraph = field(default_factory=SemanticScreenGraph)


@dataclass
class VisionIntelligenceLayer:
    """Persistent visual intelligence state across observation cycles."""
    latest_observation: Optional[VisionObservation] = None
    element_cache: Dict[str, DetectedElement] = field(default_factory=dict)  # label -> element
    graph_history: List[SemanticScreenGraph] = field(default_factory=list)
    confidence: float = 1.0
