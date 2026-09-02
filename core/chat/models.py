"""
core/chat/models.py — Chat Layer Data Models.

Định nghĩa toàn bộ data object cho tầng Chat:
- ChatMessage: đơn vị hội thoại
- IntentType / IntentClassification: kết quả phân loại ý định
- ParsedGoalSpec: GoalSpecification được parse từ JSON của LLM (typed object, KHÔNG dùng dict thô)
- ExecutionResult: kết quả thực thi từ Runtime, đủ thông tin để LLM tổng hợp câu trả lời
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class IntentType(str, Enum):
    """
    Phân loại ý định người dùng.
    Dùng để quyết định luồng xử lý TRƯỚC khi gọi LLM tốn token.
    """
    CHAT = "chat"               # Giao tiếp xã giao, hỏi đáp chung: "chào", "cảm ơn"
    QUESTION = "question"       # Câu hỏi thông tin: "Notepad là gì?"
    AGENT = "agent"             # Yêu cầu hành động thực thi: "Mở Notepad"
    REASONING = "reasoning"     # Yêu cầu suy luận: "So sánh A và B"
    MEMORY_UPDATE = "memory_update"   # Cập nhật tri thức: "Nhớ rằng tôi thích dark mode"
    CLARIFICATION = "clarification"  # Làm rõ yêu cầu trước đó
    UNKNOWN = "unknown"


@dataclass
class ChatMessage:
    """Đơn vị hội thoại trong Conversation History."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: ChatRole = ChatRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls(role=ChatRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str, metadata: Optional[Dict[str, Any]] = None) -> "ChatMessage":
        return cls(role=ChatRole.ASSISTANT, content=content, metadata=metadata or {})

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        return cls(role=ChatRole.SYSTEM, content=content)


@dataclass
class IntentClassification:
    """
    Kết quả phân loại ý định — quyết định luồng xử lý (chat vs agent vs question...).
    Không gọi LLM với chi phí token cao cho những ý định đơn giản.
    """
    intent: IntentType = IntentType.UNKNOWN
    confidence: float = 0.0
    reasoning: str = ""
    requires_runtime: bool = False
    requires_llm: bool = True

    @property
    def is_agent_request(self) -> bool:
        return self.intent == IntentType.AGENT

    @property
    def is_simple_chat(self) -> bool:
        return self.intent == IntentType.CHAT


@dataclass
class ParsedGoalSpec:
    """
    GoalSpecification được parse từ JSON output của LLM.
    
    Đây là Typed Object — không dùng dict thô trong toàn bộ hệ thống từ đây về sau.
    LLM trả JSON -> parse thành ParsedGoalSpec -> Planner nhận ParsedGoalSpec.
    """
    intent: str = ""                                # e.g. "launch_application", "web_search"
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    capability_requirements: List[str] = field(default_factory=list)  # e.g. ["desktop"], ["browser"]
    priority: str = "normal"                        # low / normal / high / critical
    expected_result: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""                             # LLM giải thích tại sao chọn intent này
    confidence: float = 1.0                         # Mức độ chắc chắn của LLM (0.0–1.0)
    raw_json: str = ""                              # Lưu JSON gốc để debug

    def is_valid(self) -> bool:
        """GoalSpec hợp lệ khi có intent (khác unknown) và confidence >= 0.5."""
        return bool(self.intent and self.intent != "unknown" and self.confidence >= 0.5)

    def requires_desktop(self) -> bool:
        return "desktop" in self.capability_requirements

    def requires_browser(self) -> bool:
        return "browser" in self.capability_requirements

    def requires_vision(self) -> bool:
        return "vision" in self.capability_requirements


@dataclass
class ExecutionResult:
    """
    Kết quả thực thi từ Runtime — đủ thông tin để LLM tổng hợp câu trả lời tự nhiên.
    Tuyệt đối KHÔNG trả về bool hay string thô.
    """
    success: bool = False
    runtime: str = ""                               # e.g. "desktop", "browser", "vision"
    intent: str = ""                                # intent đã thực thi
    duration_ms: float = 0.0
    artifacts: List[Dict[str, Any]] = field(default_factory=list)  # files, screenshots, URLs...
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[str] = None
    recovery_attempted: bool = False
    recovery_success: bool = False
    output_data: Dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> str:
        """Human-readable summary cho LLM Response Builder."""
        if self.success:
            return (
                f"Thực thi thành công: intent='{self.intent}' | runtime='{self.runtime}' | "
                f"thời gian={self.duration_ms:.0f}ms"
            )
        return (
            f"Thực thi thất bại: intent='{self.intent}' | lỗi='{self.error}' | "
            f"recovery={'Đã thử' if self.recovery_attempted else 'Chưa thử'}"
        )
