# Đặc tả Model Context Protocol (MCP Specification)

Tài liệu này đặc tả cách thức Eric tích hợp và mở rộng hệ thống bằng giao thức **Model Context Protocol (MCP)** của Anthropic.

## Nội dung sẽ phát triển:
1. **MCP Client/Server Architecture**: Cách thức Brain (MCP Client) kết nối tới các MCP Server cục bộ hoặc từ xa.
2. **Định nghĩa Resource & Tool**: Chuẩn hóa cách thức mô tả các tài nguyên (Resources) và công cụ (Tools) thông qua schema MCP.
3. **Cơ chế Bảo mật & Cấp quyền (Permission Gates)**: Cách hệ thống hỏi ý kiến người dùng trước khi thực thi các tool nhạy cảm được cung cấp qua MCP.
