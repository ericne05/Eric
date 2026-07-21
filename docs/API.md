# Đặc tả Điểm Kết Nối API (API Specification)

Tài liệu này đặc tả giao thức truyền thông và API giữa các thành phần khác nhau của ứng dụng Eric.

## Nội dung sẽ phát triển:
1. **API nội bộ (Internal IPC)**: Giao tiếp giữa Desktop UI (ví dụ: Electron/Tauri frontend) và Core Brain (backend) qua IPC hoặc WebSockets nội bộ.
2. **Giao tiếp Agent Server**: Các điểm kết nối HTTP/WebSocket mà `apps/server` cung cấp cho các agent chạy độc lập bên ngoài hoặc các web-hook.
3. **Mô tả cấu trúc dữ liệu JSON**: Các gói tin trao đổi chuẩn (như Event Payload, Tool Execution request, Tool Execution response).
