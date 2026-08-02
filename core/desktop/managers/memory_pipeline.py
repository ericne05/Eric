"""
Desktop Memory Pipeline.
"""

from typing import Any, Dict, List

from core.desktop.models import UIAccessibilitySnapshot


class DesktopMemoryPipeline:
    """
    Transforms UIAutomation Accessibility Tree snapshots into Markdown Semantic Chunks.
    Prepares desktop UI context for VectorDB storage and RAG retrieval.
    """

    def process_snapshot(self, snapshot: UIAccessibilitySnapshot, window_title: str = "Desktop Window") -> List[Dict[str, Any]]:
        """
        Converts a UIAccessibilitySnapshot into a list of semantic chunks with headers.
        """
        markdown_text = self._ui_tree_to_markdown(snapshot.tree_data, window_title)
        chunks = self._chunk_markdown(markdown_text, window_title)
        return chunks

    def _ui_tree_to_markdown(self, tree_data: Dict[str, Any], window_title: str) -> str:
        lines = [f"# Window: {window_title}\n"]
        
        elements = tree_data.get("children", []) if isinstance(tree_data, dict) else []
        for elem in elements:
            role = elem.get("role", "element")
            name = elem.get("name", "unnamed")
            bounds = elem.get("bounds", "")
            lines.append(f"## {role.title()}: {name}")
            lines.append(f"- Bounds: {bounds}")
            if "text" in elem:
                lines.append(f"- Text Content: {elem['text']}")
            lines.append("")

        return "\n".join(lines)

    def _chunk_markdown(self, markdown_text: str, window_title: str) -> List[Dict[str, Any]]:
        sections = markdown_text.split("\n## ")
        chunks = []

        header = sections[0]
        for section in sections[1:]:
            content = "## " + section
            title = section.split("\n")[0]
            chunks.append({
                "header": title,
                "content": content,
                "metadata": {
                    "window_title": window_title,
                    "source": "desktop_ui_automation"
                }
            })

        if not chunks and markdown_text:
            chunks.append({
                "header": window_title,
                "content": markdown_text,
                "metadata": {
                    "window_title": window_title,
                    "source": "desktop_ui_automation"
                }
            })

        return chunks
