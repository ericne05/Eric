# Đặc tả Đăng ký Công cụ (Tool Specification Schema)

Tài liệu này đặc tả cách định nghĩa và đăng ký các Tool trong `Tool Registry` của Eric.

## Nội dung sẽ phát triển:
1. **JSON Schema chuẩn**: Quy định cách khai báo tên công cụ, mô tả chi tiết (để LLM hiểu khi nào nên dùng), danh sách các tham số đầu vào và kiểu dữ liệu (string, number, boolean, object, array).
2. **Quản lý phiên bản Tool (Versioning)**: Đảm bảo tương thích ngược khi cập nhật tham số hoặc logic của Tool.
3. **Ví dụ thực tế**: Khai báo mẫu cho một số công cụ như `screenshot_desktop`, `read_text_file`, `navigate_url`.
