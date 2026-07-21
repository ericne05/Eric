# Lộ trình Phát triển Dự án Eric

Lộ trình phát triển của Eric được phân chia thành 7 giai đoạn (Phase 0 đến Phase 6), đi từ việc thiết lập nền tảng kiến trúc vững chắc đến tích hợp các tính năng tương tác đa phương thức phức tạp.

---

## Giai đoạn 0 (Phase 0) — Chuẩn bị & Thiết kế Hệ thống
* **Mục tiêu**: Thiết lập hạ tầng quản lý mã nguồn, cấu trúc thư mục, quy chuẩn lập trình và tài liệu thiết kế ban đầu.
* **Các nhiệm vụ**:
  * [x] Tạo cấu trúc thư mục hoàn chỉnh (Workspace) tại `D:\Projects\Eric`.
  * [x] Khởi tạo các tệp gốc: `.gitignore`, `LICENSE`, `README.md`.
  * [x] Thiết lập hệ thống tài liệu thiết kế cốt lõi trong `docs/` (`Architecture.md`, `Roadmap.md`, `Decision-Log.md`).
  * [ ] Định nghĩa Quy chuẩn lập trình (`docs/Coding-Convention.md`).
* **Tiêu chí hoàn thành**: Cây thư mục của dự án trống được giữ nguyên cấu trúc bằng các tệp `.gitkeep` và tài liệu thiết kế sẵn sàng cho việc đọc hiểu kiến trúc.

---

## Giai đoạn 1 (Phase 1) — Nền tảng Kỹ thuật (Core Foundation)
* **Mục tiêu**: Xây dựng lớp hạ tầng kỹ thuật chung (infrastructure layer) theo kiến trúc hướng sự kiện làm xương sống cho toàn bộ hệ thống.
* **Các nhiệm vụ**:
  * [ ] **Logger**: Thiết lập một logger dùng chung thống nhất cho toàn bộ hệ thống (Console + Rotating File), cấm tuyệt đối việc sử dụng `console.log()` rải rác.
  * [ ] **Config Loader**: Xây dựng bộ tải cấu hình từ `configs/*.yaml` hỗ trợ nạp cấu hình bảo mật, logging, plugin, và scheduler.
  * [ ] **Dependency Injection (DI)**: Bộ chứa container giúp loại bỏ việc liên kết cứng giữa các lớp, cho phép nạp các phụ thuộc một cách linh hoạt.
  * [ ] **Event Bus**: Xương sống truyền tin (Pub/Sub Event System) phục vụ truyền phát và lắng nghe sự kiện bất đồng bộ giữa các mô-đun.
  * [ ] **Plugin Loader**: Trình tải động các plugin mở rộng nằm trong thư mục `plugins/` mà không cần sửa đổi nhân hệ thống.
  * [ ] **Service Registry**: Bộ đăng ký dịch vụ giúp quản lý và định danh các service/tool trong hệ thống.
* **Tiêu chí hoàn thành**: Hệ thống khởi tạo thành công với cấu hình, logger hoạt động, Event Bus truyền phát tin chính xác, các service được đăng ký và giải quyết qua DI.

---

## Giai đoạn 2 (Phase 2) — Giao diện Ứng dụng & Quản lý Cửa sổ (User Interface)
* **Mục tiêu**: Làm cho ứng dụng Eric "sống" bằng cách dựng giao diện đồ họa, khay hệ thống và chế độ overlay tương tác nhanh.
* **Các nhiệm vụ**:
  * [ ] **Desktop App**: Phát triển khung cửa sổ ứng dụng chính (Electron/Tauri) với giao diện cao cấp.
  * [ ] **Tray (Khay hệ thống)**: Chạy ẩn và tương tác nhanh qua biểu tượng khay hệ thống.
  * [ ] **Overlay Mode**: Cửa sổ tương tác nhanh dạng HUD nổi trên màn hình kích hoạt qua Hotkey.
  * [ ] **Window Manager**: Quản lý vị trí, kích thước và trạng thái hiển thị của các cửa sổ Eric trên desktop.
  * [ ] **Chat UI**: Dựng giao diện trò chuyện chất lượng cao, có hoạt ảnh hiển thị trạng thái suy nghĩ.
* **Tiêu chí hoàn thành**: Ứng dụng hiển thị cửa sổ, System Tray hoạt động và Chat UI sẵn sàng nhận tin nhắn đầu vào.

---

## Giai đoạn 3 (Phase 3) — Trí tuệ cốt lõi & Bộ nhớ (Brain & Memory)
* **Mục tiêu**: Tích hợp bộ não AI cục bộ phối hợp cùng cơ chế lập kế hoạch, lập luận và quản lý bộ nhớ dài hạn.
* **Các nhiệm vụ**:
  * [ ] **Brain Engine**: Kết nối LLM và điều phối luồng suy nghĩ.
  * [ ] **Planner**: Nhận yêu cầu và tự động sinh ra kế hoạch hành động (Action Plan).
  * [ ] **Reasoner**: Suy luận sâu (Deep Thinking) và đánh giá kết quả của mỗi bước.
  * [ ] **Memory Manager**: Quản lý Episodic Memory (SQLite) và Semantic Memory (Vector DB).
  * [ ] **Prompt Manager**: Phiên bản hóa và nạp động prompt từ `resources/prompts/`.
  * [ ] **Context Manager**: Quản lý cửa sổ ngữ cảnh hội thoại.
* **Tiêu chí hoàn thành**: Brain có thể nhận câu hỏi từ Chat UI, lập kế hoạch nhiệm vụ, tự suy luận từng bước và truy vấn thông tin bộ nhớ cục bộ.

---

## Giai đoạn 4 (Phase 4) — Các Agent Thực thi (Agents)
* **Mục tiêu**: Triển khai các công cụ cho phép AI tương tác trực tiếp với máy tính của người dùng.
* **Các nhiệm vụ**:
  * [ ] **Browser Agent (WebAgent)**: Triển khai kiểm soát trình duyệt Chromium qua CDP/Playwright, chia nhỏ cấu trúc điều khiển tab, DOM, tải lên/tải xuống.
  * [ ] **Windows Agent**: Thực thi các thao tác hệ điều hành như điều khiển chuột, bàn phím ảo, quản lý vị trí các cửa sổ đang mở.
  * [ ] **File Agent**: Cung cấp các công cụ đọc, viết, tìm kiếm file an toàn trong phạm vi thư mục cho phép.
  * [ ] **Terminal Agent**: Thực thi các lệnh terminal qua PowerShell/CMD trong môi trường cô lập, có cơ chế chặn các lệnh nguy hiểm.
* **Tiêu chí hoàn thành**: Action Dispatcher có thể triệu gọi thành công các Agent để mở trình duyệt, đọc file hoặc chạy lệnh PowerShell, trả về kết quả JSON chuẩn hóa.

---

## Giai đoạn 5 (Phase 5) — Suy luận & Phối hợp (Reasoning & Orchestration)
* **Mục tiêu**: Cung cấp khả năng tự giải quyết vấn đề phức tạp qua cơ chế lập kế hoạch và phối hợp đa tác nhân.
* **Các nhiệm vụ**:
  * [ ] **Planner Engine**: Nhận yêu cầu phức tạp từ người dùng và tự động sinh ra Kế hoạch Hành động (Action Plan) gồm nhiều bước.
  * [ ] **Reasoner (Deep Thinking)**: Mô hình lập luận từng bước (Chain of Thought), đánh giá tính khả thi trước khi thực thi.
  * [ ] **Multi-Agent Coordination**: Cho phép các Agent khác nhau phối hợp giải quyết nhiệm vụ chung (ví dụ: Browser Agent tải file -> File Agent giải nén -> Terminal Agent chạy script).
  * [ ] **Reflection**: Khả năng tự kiểm điểm sai lỗi. Khi một Agent báo lỗi, Planner tự động phân tích nguyên nhân và điều chỉnh kế hoạch hành động tiếp theo.
* **Tiêu chí hoàn thành**: Eric có thể giải quyết các yêu cầu đa bước (Multi-step Tasks) mà không cần sự can thiệp của con người giữa các bước.

---

## Giai đoạn 6 (Phase 6) — Tương tác Đa phương thức (Multimodal & Automation)
* **Mục tiêu**: Tích hợp các khả năng nghe, nói, nhìn và tự động hóa toàn diện quy trình máy tính.
* **Các nhiệm vụ**:
  * [ ] **Voice Interface**: Tích hợp module STT và TTS cục bộ (Whisper & Edge-TTS) cho phép giao tiếp hoàn toàn bằng giọng nói.
  * [ ] **Computer Vision**: Khả năng phân tích hình ảnh màn hình, xác định vị trí các nút bấm thông qua chụp ảnh màn hình (Screenshot) và OCR.
  * [ ] **Complex Workflow Automation**: Cơ chế ghi lại và phát lại thao tác (Macro recording) kết hợp lập luận AI để tự động hóa quy trình nghiệp vụ lặp đi lặp lại.
* **Tiêu chí hoàn thành**: Người dùng có thể ra lệnh bằng giọng nói, Eric tự chụp ảnh màn hình, nhận diện giao diện đồ họa và thực hiện tự động hóa hoàn toàn tác vụ.
