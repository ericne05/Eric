# ERIC CONSTITUTION — Các Nguyên Tắc Bất Biến (Immutable Principles)

> **Luật Bất Biến của Dự Án Eric**  
> Mọi AI và lập trình viên tham gia phát triển bắt buộc tuân thủ 100%.

---

## 📜 8 Nguyên Tắc Bất Biến

1. **Không vượt cấp Kernel (Never Bypass Kernel)**:
   Mọi luồng khởi động, tắt ứng dụng và wiring giữa các thành phần cốt lõi phải thông qua Kernel. Không module nào tự khởi tạo hoặc tự quản lý vòng đời độc lập ngoài Kernel.

2. **Brain không bao giờ biết chi tiết triển khai của Agent (Decoupled Brain & Agent)**:
   Brain và Planner chỉ làm việc với định dạng trừu tượng (JSON command & Tool Schema). Brain tuyệt đối không import thư viện hoặc gọi trực tiếp mã nguồn của Agent.

3. **Agents không bao giờ gọi trực tiếp nhau (Agents Isolation)**:
   Các Agent (`BrowserAgent`, `WindowsAgent`, `FileAgent`) hoạt động hoàn toàn độc lập. Việc phối hợp giữa các Agent phải do Planner & Dispatcher điều phối thông qua EventBus hoặc Task breakdown.

4. **Mọi giao tiếp trạng thái đều đi qua EventBus (Event-Driven Isolation)**:
   Các thành phần không gọi hàm trực tiếp của nhau trừ khi đăng ký qua Service Registry và truyền nhận thông điệp qua EventBus.

5. **Bộ nhớ không giao tiếp trực tiếp với UI (Memory-UI Separation)**:
   UI chỉ hiển thị dữ liệu và gửi sự kiện tương tác của người dùng. UI không truy cập trực tiếp SQLite, Vector DB hay Memory Manager. Mọi truy vấn bộ nhớ phải do Brain/Context Manager xử lý.

6. **Mọi Module phải kiểm thử được (Testability Rule)**:
   Không thiết kế class dưới dạng Singleton cứng trừ khi có quy định ADR. Dependency Injection phải được ưu tiên để cho phép giả lập (mock) dependencies trong Unit Tests.

7. **Mọi Public API phải có Unit Test (Mandatory Test Coverage)**:
   Mỗi phương thức hoặc hàm public mới tạo đều bắt buộc phải có ít nhất 1 Unit test bao phủ cả happy path và error path. Coverage mục tiêu ≥90%.

8. **Cơ chế Thất bại Nhanh (Fail-Fast Policy)**:
   Không nuốt ngoại lệ (silent try/except) hoặc trả về fallback giả tạo làm che giấu lỗi gốc. Lỗi phải được phát hiện sớm, log đầy đủ và xử lý theo đúng quy trình.
