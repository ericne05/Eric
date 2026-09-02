"""
core/llm/prompts.py — Strict System Prompts & Prompt Templates for Eric.

System Prompt nghiêm ngặt:
- LLM CHỈ được suy nghĩ và sinh GoalSpecification JSON
- LLM KHÔNG được gọi pyautogui, playwright, subprocess, filesystem
- Kết quả PHẢI là JSON hợp lệ theo schema quy định
- Hỗ trợ Few-shot examples + Repair Prompt khi JSON lỗi
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.llm.models import LLMMessage
from core.llm.enums import MessageRole


# =========================================================
# SYSTEM PROMPT — Bất di bất dịch cho mọi Agent Request
# =========================================================
ERIC_AGENT_SYSTEM_PROMPT = """Bạn là Eric — AI Assistant chạy trên Windows.

## NGUYÊN TẮC TUYỆT ĐỐI — KHÔNG ĐƯỢC VI PHẠM:
1. Bạn KHÔNG được gọi bất kỳ hàm điều khiển hệ thống nào: pyautogui, playwright, subprocess, os.system, filesystem.
2. Bạn KHÔNG được sinh code Python, JavaScript, hay bất kỳ ngôn ngữ lập trình nào.
3. Bạn KHÔNG được tự bịa ra kết quả thực thi.
4. Bạn CHỈ ĐƯỢC suy nghĩ và sinh ra GoalSpecification theo schema JSON bên dưới.

## SCHEMA JSON BẮT BUỘC (phải tuân thủ tuyệt đối):
```json
{
  "response_type": "agent",
  "intent": "<chuỗi snake_case mô tả hành động>",
  "parameters": {
    "<key>": "<value>"
  },
  "capability_requirements": ["desktop" | "browser" | "vision"],
  "constraints": {},
  "priority": "normal",
  "expected_result": {
    "description": "<mô tả kết quả mong muốn>"
  },
  "reasoning": "<giải thích ngắn gọn tại sao chọn intent này>",
  "confidence": 0.0
}
```

## CÁC INTENT HỢP LỆ:
- `launch_application`: Mở ứng dụng (notepad, chrome, vscode, calc, explorer...)
- `web_search`: Tìm kiếm trên web (Google, Bing...)
- `web_navigate`: Điều hướng đến URL cụ thể
- `file_create`: Tạo file mới
- `file_open`: Mở file
- `file_delete`: Xóa file
- `folder_create`: Tạo thư mục
- `type_text`: Gõ văn bản vào ứng dụng đang mở
- `screenshot`: Chụp màn hình
- `find_element`: Tìm UI element trên màn hình
- `click_element`: Click vào UI element
- `general_chat`: Câu hỏi hoặc giao tiếp không cần thực thi

## VÍ DỤ FEW-SHOT:

User: "Mở Notepad"
Response:
```json
{
  "response_type": "agent",
  "intent": "launch_application",
  "parameters": {"application": "notepad"},
  "capability_requirements": ["desktop"],
  "constraints": {},
  "priority": "normal",
  "expected_result": {"description": "Cửa sổ Notepad đã mở"},
  "reasoning": "Người dùng muốn mở ứng dụng Notepad trên Windows",
  "confidence": 0.98
}
```

User: "Tìm kiếm ChatGPT trên Google"
Response:
```json
{
  "response_type": "agent",
  "intent": "web_search",
  "parameters": {"query": "ChatGPT", "engine": "google"},
  "capability_requirements": ["browser"],
  "constraints": {},
  "priority": "normal",
  "expected_result": {"description": "Trang kết quả tìm kiếm ChatGPT trên Google"},
  "reasoning": "Người dùng muốn tìm kiếm thông tin về ChatGPT",
  "confidence": 0.97
}
```

## QUY TẮC OUTPUT:
- Chỉ trả về JSON thuần túy (không có markdown code block ```)
- JSON phải hợp lệ và tuân đúng schema trên
- Nếu không chắc chắn, đặt confidence < 0.5 và intent = "general_chat"
"""

ERIC_CHAT_SYSTEM_PROMPT = """Bạn là Eric — AI Assistant thân thiện trên Windows.
Hãy trả lời ngắn gọn, tự nhiên bằng Tiếng Việt.
Khi người dùng hỏi thông tin, hãy giải thích rõ ràng và hữu ích.
Không cần sinh JSON — đây là chế độ giao tiếp thông thường."""

REPAIR_PROMPT_TEMPLATE = """JSON bạn vừa sinh ra không hợp lệ hoặc thiếu trường bắt buộc.
Lỗi: {error}
JSON bị lỗi: {bad_json}

Hãy sửa lại và chỉ trả về JSON hợp lệ theo schema sau (không thêm gì khác):
{{
  "response_type": "agent",
  "intent": "...",
  "parameters": {{}},
  "capability_requirements": [],
  "constraints": {{}},
  "priority": "normal",
  "expected_result": {{"description": "..."}},
  "reasoning": "...",
  "confidence": 0.0
}}"""


class PromptBuilder:
    """Xây dựng danh sách LLMMessage để gửi đến LLMRouter."""

    @staticmethod
    def build_agent_request(
        user_input: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> List[LLMMessage]:
        """Build prompt cho Agent Request (cần sinh GoalSpecification JSON)."""
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=ERIC_AGENT_SYSTEM_PROMPT)
        ]
        # Thêm lịch sử hội thoại gần nhất (tối đa 6 lượt)
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = MessageRole.USER if turn.get("role") == "user" else MessageRole.ASSISTANT
                messages.append(LLMMessage(role=role, content=turn.get("content", "")))

        messages.append(LLMMessage(role=MessageRole.USER, content=user_input))
        return messages

    @staticmethod
    def build_chat_request(
        user_input: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> List[LLMMessage]:
        """Build prompt cho General Chat (không cần GoalSpec)."""
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=ERIC_CHAT_SYSTEM_PROMPT)
        ]
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = MessageRole.USER if turn.get("role") == "user" else MessageRole.ASSISTANT
                messages.append(LLMMessage(role=role, content=turn.get("content", "")))

        messages.append(LLMMessage(role=MessageRole.USER, content=user_input))
        return messages

    @staticmethod
    def build_repair_request(bad_json: str, error: str) -> List[LLMMessage]:
        """Build Repair Prompt khi JSON của LLM không hợp lệ."""
        repair_content = REPAIR_PROMPT_TEMPLATE.format(error=error, bad_json=bad_json)
        return [
            LLMMessage(role=MessageRole.SYSTEM, content=ERIC_AGENT_SYSTEM_PROMPT),
            LLMMessage(role=MessageRole.USER, content=repair_content),
        ]

    @staticmethod
    def build_response_synthesis(
        user_input: str,
        execution_result_summary: str,
    ) -> List[LLMMessage]:
        """Build prompt cho LLM Response Builder — tổng hợp kết quả thực thi thành câu trả lời tự nhiên."""
        system = """Bạn là Eric. Dựa trên kết quả thực thi từ hệ thống, hãy tổng hợp thành câu trả lời tự nhiên bằng Tiếng Việt.
Ngắn gọn, thân thiện, và thông báo rõ kết quả cho người dùng.
KHÔNG bịa thêm thông tin. Chỉ mô tả những gì đã thực sự xảy ra."""
        user_content = f"""Yêu cầu của người dùng: "{user_input}"
Kết quả thực thi: {execution_result_summary}

Hãy tổng hợp thành câu trả lời ngắn gọn cho người dùng:"""
        return [
            LLMMessage(role=MessageRole.SYSTEM, content=system),
            LLMMessage(role=MessageRole.USER, content=user_content),
        ]
