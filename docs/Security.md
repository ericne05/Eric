# Đặc tả An toàn và Bảo mật (Security Specification)

Tài liệu này xác định các ranh giới bảo mật và cơ chế bảo vệ hệ thống máy tính của người dùng khi Eric hoạt động.

## Nội dung sẽ phát triển:
1. **Ranh giới thực thi (Execution Sandboxing)**: Cô lập môi trường chạy lệnh của Terminal Agent và giới hạn quyền truy cập thư mục của File Agent.
2. **Quyền nhạy cảm (Permission Prompts)**: Danh sách các tác vụ bắt buộc phải hiển thị hộp thoại xác nhận của người dùng (ví dụ: gửi email, xóa file hệ thống, tải tệp thực thi `.exe`).
3. **Bảo mật API Keys & Tokens**: Phương pháp lưu trữ an toàn các API Key (sử dụng Windows Credential Manager hoặc các giải pháp mã hóa cục bộ tương đương).
4. **Bộ lọc dữ liệu đầu ra (Redaction filter)**: Tự động phát hiện và che giấu thông tin cá nhân (PII), mật khẩu hoặc mã token trước khi gửi dữ liệu lên LLM đám mây.
