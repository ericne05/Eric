# Nhật ký Quyết định Kiến trúc (Architecture Decision Log)

Tài liệu này lưu trữ các quyết định thiết kế kiến trúc quan trọng của dự án **Eric**, ghi nhận lý do tại sao các lựa chọn được đưa ra và bối cảnh lịch sử của chúng.

---

## [ADR-001] Tái cấu trúc cấu trúc thư mục dự án

* **Trạng thái**: Đã phê duyệt (Approved)
* **Ngày đưa ra quyết định**: 2026-07-22
* **Tác giả**: Người dùng & Antigravity

### Bối cảnh (Context)
Cấu trúc thư mục ban đầu sử dụng thư mục `data/` chung chung để lưu trữ bộ nhớ cục bộ và đặt mã nguồn logic của bộ não (`brain`) ngay trong thư mục ứng dụng chạy được (`apps/`). Khi mở rộng dự án trong nhiều năm, việc thiếu các thư mục chuyên trách như cấu hình (`configs/`), plugin (`plugins/`), tài nguyên AI (`resources/`), và kiểm thử (`tests/`) có thể dẫn tới code lộn xộn và khó bảo trì.

### Quyết định (Decision)
1. Thay đổi tên thư mục từ `data/` thành `storage/` để thể hiện đúng vai trò là nơi lưu trữ trạng thái cục bộ (SQLite, Vector DB, Logs, Models, Profiles...).
2. Bổ sung thư mục `core/` làm "trái tim" chứa toàn bộ logic AI cốt lõi (brain, planner, reasoner, dispatcher, memory, context, scheduler, events). Thư mục `apps/` chỉ chứa các chương trình thực thi được (desktop UI, launcher, server).
3. Thêm các thư mục:
   * `configs/` để chứa cấu hình hệ thống tách biệt (`app.yaml`, `llm.yaml`, v.v.).
   * `plugins/` hỗ trợ kiến trúc plugin động ngay từ đầu.
   * `resources/` chứa prompt, templates, icons, voices, v.v.
   * `tests/` để tích hợp kiểm thử đơn vị, kiểm thử tích hợp và kiểm thử agent sớm.

### Hệ quả (Consequences)
* **Tích cực**: Phân chia trách nhiệm rõ ràng (Separation of Concerns). Logic xử lý AI hoàn toàn độc lập với phần hiển thị UI hay chạy ứng dụng. Việc thay đổi LLM, cấu hình hệ thống hay cập nhật các prompt không làm ảnh hưởng đến mã nguồn logic nhờ việc tách biệt sang `configs/` và `resources/`.
* **Tiêu cực**: Số lượng thư mục ban đầu tăng lên, đòi hỏi lập trình viên phải hiểu rõ quy tắc phân chia để đặt tệp tin đúng vị trí.

---

## [ADR-002] Nguyên tắc thiết kế cách ly hoàn toàn: Brain không gọi trực tiếp Agent

* **Trạng thái**: Đã phê duyệt (Approved)
* **Ngày đưa ra quyết định**: 2026-07-22
* **Tác giả**: Người dùng & Antigravity

### Bối cảnh (Context)
Trong các kiến trúc AI Agent đơn giản, bộ não (LLM/Brain) thường trực tiếp gọi các hàm API hoặc import các module điều khiển thiết bị (như duyệt web hoặc chạy terminal). Cách làm này khiến Brain bị phụ thuộc chặt chẽ (tightly coupled) vào các API cụ thể của công cụ, gây khó khăn cho việc viết unit test độc lập cho Brain hoặc hoán đổi các công cụ trong tương lai.

### Quyết định (Decision)
Thiết lập nguyên tắc kiến trúc bất biến: **Brain không được phép gọi trực tiếp bất kỳ Agent nào.**
Mọi luồng hành động đều đi qua một chuỗi trung gian bắt buộc:
`User` -> `Desktop UI` -> `Brain` -> `Planner` -> `Action Dispatcher` -> `Tool Registry` -> `Agent` -> `Result` -> `Memory`.

### Hệ quả (Consequences)
* **Tích cực**:
  * Các thành phần giao tiếp hoàn toàn qua định dạng JSON thông qua Dispatcher.
  * Có thể dễ dàng giả lập (mock) kết quả trả về từ Agent để kiểm thử Planner và Brain mà không cần thực thi hành động thật trên máy tính.
  * Có thể viết thêm Agent mới độc lập và đăng ký động vào `Tool Registry` qua giao thức MCP mà không cần thay đổi bất kỳ dòng code nào trong `core/brain` hay `core/planner`.
* **Tiêu cực**: Gia tăng một số lớp trung gian (indirection layer) trong code, đòi hỏi cấu trúc đăng ký công cụ (Tool Registry Schema) phải được chuẩn hóa từ đầu.

---

## [ADR-003] Phân tách mô-đun chi tiết cho Browser Agent

* **Trạng thái**: Đã phê duyệt (Approved)
* **Ngày đưa ra quyết định**: 2026-07-22
* **Tác giả**: Người dùng & Antigravity

### Bối cảnh (Context)
Browser Agent chịu trách nhiệm tương tác web là một tác nhân phức tạp. Việc triển khai tất cả các logic (như quản lý tab, DOM parsing, tải xuống, CDP connection, cookies, screenshot) vào một hoặc hai tệp mã nguồn lớn sẽ dẫn đến tình trạng tệp code dài hàng nghìn dòng, rất khó bảo trì và debug.

### Quyết định (Decision)
Tách nhỏ Browser Agent ngay từ đầu thành các thành phần mô-đun riêng biệt dưới thư mục `tools/browser-agent/`:
* `browser/` - Khởi tạo và quản lý tiến trình Chrome.
* `tabs/` - Trạng thái và điều khiển các tab trình duyệt.
* `dom/` - Phân tích cấu trúc trang web và xác định phần tử tương tác.
* `network/` - Lắng nghe, lọc và can thiệp lưu lượng mạng.
* `cookies/` - Quản lý phiên làm việc và cookie.
* `download/` / `upload/` - Xử lý truyền nhận tệp qua web.
* `cdp/` - Giao tiếp trực tiếp với Chrome DevTools Protocol.
* `screenshot/` - Chụp ảnh màn hình và xử lý phục vụ visual.

### Hệ quả (Consequences)
* **Tích cực**: Mỗi thư mục con chịu trách nhiệm cho một tính năng cụ thể giúp mã nguồn Browser Agent sạch sẽ, dễ viết unit test độc lập và dễ phân công nhiều nhà phát triển cùng làm việc.
* **Tiêu cực**: Đòi hỏi thiết lập luồng import nội bộ của Agent cẩn thận để tránh import vòng quanh (circular dependencies).

---

## [ADR-004] Eric là hệ thống hướng sự kiện (Event-Driven System), không gọi hàm trực tiếp

* **Trạng thái**: Đã phê duyệt (Approved)
* **Ngày đưa ra quyết định**: 2026-07-22
* **Tác giả**: Người dùng & Antigravity

### Bối cảnh (Context)
Khi tích hợp nhiều thành phần như UI, Brain, Planner, Agents và Plugins, việc các thành phần này gọi hàm trực tiếp của nhau (direct function calls) sẽ tạo ra mạng lưới phụ thuộc chéo cực kỳ phức tạp. Điều này làm cho hệ thống trở nên cứng nhắc, rất khó để phát triển độc lập hoặc thay thế các module khi dự án lớn dần qua nhiều năm.

### Quyết định (Decision)
Thiết lập nguyên tắc kiến trúc: **Eric là một hệ thống hướng sự kiện (Event-Driven), truyền nhận tin bất đồng bộ thông qua Event Bus.**
* **Không gọi hàm trực tiếp**: Các module không được phép gọi trực tiếp logic của nhau trừ khi đăng ký qua Service Registry và giao tiếp qua Event Bus.
* **Brain cách ly**: Brain không biết cụ thể Agent nào đang chạy, nó chỉ phát ra các yêu cầu công cụ (events/commands) lên Event Bus.
* **Agent độc lập**: Agent nhận lệnh từ Event Bus mà không cần biết ai hoặc module nào tạo ra yêu cầu đó.
* **UI mỏng (Thin UI)**: UI chỉ chịu trách nhiệm hiển thị trạng thái và phát sự kiện tương tác của người dùng, hoàn toàn không chứa bất kỳ logic suy luận hay nghiệp vụ AI nào.

### Hệ quả (Consequences)
* **Tích cực**:
  * Các thành phần liên kết lỏng lẻo (loose coupling), cực kỳ dễ mở rộng. Ta có thể thêm một Plugin hay Agent mới bằng cách đơn giản là đăng ký nó lắng nghe các Event tương ứng trên Event Bus.
  * Dễ dàng debug và giám sát (Monitoring): Chỉ cần lắng nghe Event Bus là có thể theo dõi được toàn bộ luồng hoạt động của Eric.
  * Cực kỳ thuận lợi cho việc kiểm thử tích hợp (Integration testing) bằng cách phát sự kiện giả lập và kiểm tra sự kiện trả về.
* **Tiêu cực**: Việc theo dõi luồng code tĩnh (static code flow) sẽ khó hơn vì không có các cuộc gọi hàm trực tiếp rõ ràng. Cần phải có tài liệu sự kiện (Event Schemas) và tài liệu hóa luồng đi của sự kiện thật tốt.

---

## [ADR-005] Đóng băng công nghệ và chuẩn hóa giao tiếp (Tech Stack Freeze)

* **Trạng thái**: Đã phê duyệt (Approved)
* **Ngày đưa ra quyết định**: 2026-07-22
* **Tác giả**: Người dùng & Antigravity

### Bối cảnh (Context)
Nếu không thống nhất trước tập hợp công nghệ (Tech Stack) và các cấu trúc dữ liệu cơ bản (sự kiện, vòng đời agent, chuẩn đầu ra của tool) ngay từ đầu, dự án sẽ dễ rơi vào trạng thái không đồng nhất khi nhiều nhà phát triển tham gia, dẫn tới việc phải viết lại mã nguồn khi kết hợp các module (ví dụ: giao diện Tauri/React và Core Python).

### Quyết định (Decision)
1. **Tech Stack**: Đóng băng stack công nghệ với React + Tauri cho giao diện UI, Python cho nhân Core AI, SQLite/ChromaDB cho lưu trữ và các thư viện chuyên biệt (Playwright, Faster-Whisper, Piper).
2. **Quy ước tên Event**: Tất cả các module phải tuân thủ nghiêm ngặt định dạng đặt tên sự kiện: `[namespace].[component].[action]` (ví dụ: `ui.message.received`, `brain.plan.created`).
3. **Quy chuẩn Agent**: Đồng nhất 7 trạng thái vòng đời của tất cả các Agent: `Initialize` -> `Load Config` -> `Register` -> `Ready` -> `Running` -> `Paused` -> `Stopped`.
4. **Quy chuẩn Tool**: Mọi công cụ thực thi của Agent đều bắt buộc trả về một cấu trúc JSON thống nhất có chứa các trường: `success`, `data`, `error`, `execution_time`, và `agent`.
5. **Phân cấp Memory**: Tổ chức bộ nhớ thành 5 lớp từ tạm thời (Working Memory) đến vĩnh viễn (Vector Memory).

### Hệ quả (Consequences)
* **Tích cực**:
  * Đảm bảo tính nhất quán tuyệt đối về kiểu dữ liệu trên toàn bộ hệ thống. Brain và Action Dispatcher có thể xử lý kết quả của bất kỳ Agent nào theo cùng một cách thức.
  * Tránh xung đột thiết kế khi bắt tay vào code các module độc lập.
* **Tiêu cực**: Đòi hỏi các Agent viết bằng Python phải wrap dữ liệu trả về theo đúng chuẩn JSON, ngay cả khi gặp lỗi.


