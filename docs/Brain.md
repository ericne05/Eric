# Đặc tả Bộ não AI (Brain Specification)

Tài liệu này sẽ đặc tả thiết kế chi tiết cho thành phần `core/brain` và `core/planner` của Eric.

## Nội dung sẽ phát triển:
1. **Mô hình lập luận (Reasoning Paradigm)**: Chain of Thought, ReAct, hay Plan-and-Solve.
2. **Quản lý Ngữ cảnh (Context Window Management)**: Chiến lược cắt tỉa và nén hội thoại.
3. **Cơ chế lập kế hoạch (Planner)**: Cách thức phân rã yêu cầu của người dùng thành đồ thị tác vụ (Task Graph).
4. **Cơ chế tự đánh giá (Reflection / Self-Correction)**: Đánh giá lỗi từ Agent và lập kế hoạch sửa lỗi.
