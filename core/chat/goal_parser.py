"""
core/chat/goal_parser.py — LLM Output Parser.

Parse JSON output từ LLM thành ParsedGoalSpec typed object.
Hỗ trợ Repair Prompt khi JSON không hợp lệ.
LLM trả JSON -> GoalParser -> ParsedGoalSpec -> Planner.
Từ đây về sau KHÔNG dùng dict thô.
"""

from __future__ import annotations

import json
import re
import logging
from typing import Any, Dict, Optional

from core.chat.models import ParsedGoalSpec

logger = logging.getLogger(__name__)


class GoalParser:
    """
    Parse raw JSON string từ LLM output thành ParsedGoalSpec object.
    
    Xử lý các trường hợp:
    1. JSON thuần túy -> parse trực tiếp
    2. JSON trong markdown code block (```json...```) -> extract trước
    3. JSON lỗi -> log + trả ParsedGoalSpec rỗng (caller sẽ gọi Repair Prompt)
    """

    def parse(self, raw_output: str, original_input: str = "") -> Optional[ParsedGoalSpec]:
        """
        Parse LLM output thành ParsedGoalSpec.
        Trả về None nếu parse thất bại (caller cần gọi Repair Prompt).
        """
        if not raw_output or not raw_output.strip():
            return None

        # Thử extract JSON từ markdown code block nếu có
        json_str = self._extract_json(raw_output.strip())

        try:
            data: Dict[str, Any] = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"[GoalParser] JSON parse error: {e} | raw='{raw_output[:100]}'")
            return None

        intent = data.get("intent", "").strip()
        if not intent:
            return None

        return ParsedGoalSpec(
            intent=intent,
            parameters=data.get("parameters", {}),
            constraints=data.get("constraints", {}),
            capability_requirements=data.get("capability_requirements", []),
            priority=data.get("priority", "normal"),
            expected_result=data.get("expected_result", {}),
            metadata=data.get("metadata", {}),
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 1.0)),
            raw_json=json_str,
        )

    def _extract_json(self, text: str) -> str:
        """Extract JSON từ text — loại bỏ markdown code blocks nếu có."""
        # Pattern: ```json ... ``` hoặc ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        # Thử tìm { ... } trực tiếp nếu có text xung quanh
        match = re.search(r"(\{[\s\S]+\})", text)
        if match:
            return match.group(1).strip()
        return text

    def is_chat_response(self, raw_output: str) -> bool:
        """Kiểm tra xem LLM output có phải là chat response thông thường (không phải JSON)."""
        stripped = raw_output.strip()
        return not stripped.startswith("{") and "intent" not in stripped
