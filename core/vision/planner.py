"""
Visual Planner.

Uses a SemanticScreenGraph to answer Planner queries:
  - "Where should I click to press Submit?"
  - "Is there an input field for username?"
  - "What text is visible near the error icon?"
"""

from typing import Any, Dict, List, Optional, Tuple

from core.vision.enums import VisualElementType
from core.vision.models import BoundingBox, GraphNode, SemanticScreenGraph


class ClickTarget:
    """A resolved click target derived from the Semantic Screen Graph."""

    def __init__(self, x: int, y: int, label: str, confidence: float = 1.0):
        self.x = x
        self.y = y
        self.label = label
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"ClickTarget({self.label!r} @ ({self.x}, {self.y}) conf={self.confidence:.2f})"


class VisualPlanner:
    """
    Plans clicks and interactions by reasoning over a SemanticScreenGraph.
    Used when UIAutomation selectors fail and the agent must rely on vision.
    """

    def find_click_target(
        self,
        graph: SemanticScreenGraph,
        label_query: str,
        element_types: Optional[List[VisualElementType]] = None,
    ) -> Optional[ClickTarget]:
        """
        Find the best click target for a label query.

        Search priority:
          1. Interactive element whose label matches exactly.
          2. Interactive element whose label partially matches.
          3. Text block that LABEL_OF-links to an interactive element.
          4. Any node containing matching text.
        """
        # Phase 1 & 2: Direct label match on interactive elements
        for exact in (True, False):
            node = graph.find_by_label(label_query, partial=not exact)
            if node and node.bounds:
                # Filter by element type if specified
                if node.element and element_types:
                    if node.element.element_type not in element_types:
                        continue
                confidence = 1.0 if exact else 0.85
                return ClickTarget(
                    x=node.bounds.center_x,
                    y=node.bounds.center_y,
                    label=node.label,
                    confidence=confidence,
                )

        # Phase 3: Text block that is a LABEL_OF an interactive element
        from core.vision.enums import GraphEdgeType
        for edge in graph.edges:
            if edge.edge_type == GraphEdgeType.LABEL_OF:
                src = graph.nodes.get(edge.source_id)
                tgt = graph.nodes.get(edge.target_id)
                if src and src.text_block and label_query.lower() in src.text_block.text.lower():
                    if tgt and tgt.bounds:
                        return ClickTarget(
                            x=tgt.bounds.center_x,
                            y=tgt.bounds.center_y,
                            label=src.label,
                            confidence=0.75,
                        )

        # Phase 4: Text search fallback
        matches = graph.find_by_text(label_query, partial=True)
        for node in matches:
            if node.bounds:
                return ClickTarget(
                    x=node.bounds.center_x,
                    y=node.bounds.center_y,
                    label=node.label,
                    confidence=0.6,
                )

        return None

    def extract_visible_text(self, graph: SemanticScreenGraph) -> str:
        """Extract all readable text from the graph in reading order."""
        from core.vision.enums import GraphEdgeType, GraphNodeType

        # Follow FOLLOWS edges for reading order
        visited: set[str] = set()
        ordered: list[str] = []

        # Find the starting node (no FOLLOWS incoming edge)
        has_incoming_follows = {
            e.target_id for e in graph.edges if e.edge_type == GraphEdgeType.FOLLOWS
        }
        text_nodes = [
            n for n in graph.nodes.values()
            if n.node_type == GraphNodeType.TEXT_BLOCK and n.text_block
        ]
        start_nodes = [n for n in text_nodes if n.id not in has_incoming_follows]

        def _follow(node: GraphNode) -> None:
            if node.id in visited:
                return
            visited.add(node.id)
            if node.text_block:
                ordered.append(node.text_block.text)
            for edge in graph.edges:
                if edge.edge_type == GraphEdgeType.FOLLOWS and edge.source_id == node.id:
                    next_node = graph.nodes.get(edge.target_id)
                    if next_node:
                        _follow(next_node)

        for start in start_nodes:
            _follow(start)

        # Add any remaining text nodes not reachable by FOLLOWS
        for node in text_nodes:
            if node.id not in visited and node.text_block:
                ordered.append(node.text_block.text)

        return " ".join(ordered)

    def get_element_at(self, graph: SemanticScreenGraph, x: int, y: int) -> Optional[GraphNode]:
        """Return the topmost (smallest area) element that contains the given coordinates."""
        candidates = []
        for node in graph.nodes.values():
            if not node.bounds:
                continue
            b = node.bounds
            if b.x <= x <= b.x + b.width and b.y <= y <= b.y + b.height:
                candidates.append(node)
        if not candidates:
            return None
        return min(candidates, key=lambda n: n.bounds.area)
