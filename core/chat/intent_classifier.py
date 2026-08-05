"""
core/chat/intent_classifier.py — Intent Classifier.

Phân loại ý định người dùng TRƯỚC khi gọi LLM (tiết kiệm token).
Pattern-based fast path cho các ý định đơn giản.
"""

from __future__ import annotations

import re
from typing import List, Optional

from core.chat.models import IntentClassification, IntentType


class IntentClassifier:
    """
    Phân loại ý định người dùng thành các luồng xử lý:
    - CHAT: Giao tiếp xã giao -> trả lời trực tiếp (không tốn token LLM)
    - QUESTION: Câu hỏi thông tin -> LLM trả lời (chat mode, không cần Runtime)
    - AGENT: Yêu cầu hành động -> LLM sinh GoalSpec -> Planner -> Runtime
    - MEMORY_UPDATE: Cập nhật tri thức -> lưu vào Knowledge Graph
    """

    # Patterns cho CHAT (xã giao, không cần LLM Goal)
    _CHAT_PATTERNS = [
        r"^(hi|hello|hey|alo|xin chào|chào|chao|chào eric|hi eric)[\s!?]*$",
        r"^(cảm ơn|cam on|thank(s| you)|tks|thx)[\s!?]*$",
        r"^(tạm biệt|bye|goodbye|bái bai)[\s!?]*$",
        r"^(ok|okay|oke|được rồi|được|tốt lắm|good)[\s!?]*$",
    ]

    # Patterns cho AGENT (yêu cầu hành động thực thi)
    _AGENT_PATTERNS = [
        # Mở ứng dụng
        r"(mở|open|launch|chạy|start|khởi động)\s+.+",
        # Tìm kiếm
        r"(tìm kiếm|search|google|tìm|tra|lookup)\s+.+",
        # File operations
        r"(tạo|create|xóa|delete|di chuyển|move|copy|sao chép)\s+(file|folder|thư mục|tệp)",
        # Điều hướng web
        r"(vào|mở|navigate|truy cập)\s+(trang|website|web|url|http)",
        # Chụp màn hình
        r"(chụp|screenshot|capture)\s*(màn hình)?",
        # Gõ văn bản
        r"(gõ|type|nhập|viết)\s+.+\s+(vào|trong|ở)",
    ]

    # Patterns cho QUESTION
    _QUESTION_PATTERNS = [
        r".+(là gì|là cái gì|nghĩa là gì)\??",
        r"(tại sao|why|vì sao|lý do)\s+.+",
        r"(làm thế nào|how to|cách|hướng dẫn)\s+.+",
        r"(so sánh|compare|khác nhau|difference)\s+.+",
        r"(giải thích|explain)\s+.+",
    ]

    # Patterns cho MEMORY_UPDATE
    _MEMORY_PATTERNS = [
        r"(nhớ rằng|remember|ghi nhớ|lưu lại)\s+.+",
        r"(tao|tôi|mình)\s+(thích|prefer|muốn|hay dùng)\s+.+",
        r"(từ giờ|dorénavant|henceforth)\s+.+",
    ]

    def __init__(self):
        self._chat_re = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in self._CHAT_PATTERNS]
        self._agent_re = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in self._AGENT_PATTERNS]
        self._question_re = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in self._QUESTION_PATTERNS]
        self._memory_re = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in self._MEMORY_PATTERNS]

    def classify(self, text: str) -> IntentClassification:
        """Phân loại ý định từ input text của người dùng."""
        stripped = text.strip()

        # 1. Chat (xã giao) — fast path, không cần LLM
        for pattern in self._chat_re:
            if pattern.match(stripped):
                return IntentClassification(
                    intent=IntentType.CHAT,
                    confidence=0.95,
                    reasoning="Pattern khớp với giao tiếp xã giao",
                    requires_runtime=False,
                    requires_llm=False,
                )

        # 2. Memory update
        for pattern in self._memory_re:
            if pattern.search(stripped):
                return IntentClassification(
                    intent=IntentType.MEMORY_UPDATE,
                    confidence=0.85,
                    reasoning="Pattern khớp với yêu cầu cập nhật bộ nhớ",
                    requires_runtime=False,
                    requires_llm=True,
                )

        # 3. Agent request (hành động thực thi)
        for pattern in self._agent_re:
            if pattern.search(stripped):
                return IntentClassification(
                    intent=IntentType.AGENT,
                    confidence=0.88,
                    reasoning="Pattern khớp với yêu cầu hành động thực thi",
                    requires_runtime=True,
                    requires_llm=True,
                )

        # 4. Question (thông tin)
        for pattern in self._question_re:
            if pattern.search(stripped):
                return IntentClassification(
                    intent=IntentType.QUESTION,
                    confidence=0.82,
                    reasoning="Pattern khớp với câu hỏi thông tin",
                    requires_runtime=False,
                    requires_llm=True,
                )

        # 5. Fallback — gửi sang LLM để quyết định
        return IntentClassification(
            intent=IntentType.UNKNOWN,
            confidence=0.3,
            reasoning="Không nhận diện được pattern — cần LLM phân loại",
            requires_runtime=False,
            requires_llm=True,
        )
