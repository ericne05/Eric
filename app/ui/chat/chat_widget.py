"""
Chat Widget Component.
Renders chat history, markdown text, code blocks, streaming state, and status indicators.
"""

from typing import List, Optional

from app.services.session_manager import ChatMessage


class ChatWidget:
    """
    Rich Chat UI Widget representation.
    Formats messages with Markdown, code blocks, and real-time status indicators.
    """

    def __init__(self):
        self._messages: List[ChatMessage] = []

    def update_messages(self, messages: List[ChatMessage]) -> None:
        self._messages = messages

    def render_markdown(self, content: str) -> str:
        """Helper converting markdown & code blocks for display."""
        formatted = content.replace("```", "```\n")
        return formatted

    def get_rendered_messages(self) -> List[dict]:
        output = []
        for msg in self._messages:
            output.append({
                "id": msg.id,
                "sender": msg.sender,
                "content_html": self.render_markdown(msg.content),
                "timestamp": msg.timestamp.strftime("%H:%M:%S"),
                "status": msg.status_indicator,
            })
        return output
