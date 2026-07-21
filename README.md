# Eric - Personal AI Agent OS

Eric là một trợ lý AI cá nhân hoạt động cục bộ (local-first) dưới dạng Hệ điều hành Agent (Agent OS). Dự án được thiết kế để kiểm soát máy tính, duyệt web, quản lý bộ nhớ và tự động hóa các tác vụ cá nhân một cách thông minh, bảo mật và cực kỳ mô-đun.

---

## 1. Vision (Tầm nhìn)
Tạo dựng một trợ lý AI mạnh mẽ có khả năng đồng hành lâu dài cùng người dùng, học hỏi thói quen và thực hiện các tác vụ phức tạp trực tiếp trên máy tính cá nhân. Thiết kế của Eric hướng tới sự tối giản trong tích hợp nhưng vô cùng chặt chẽ trong kiến trúc, đảm bảo hệ thống có thể phát triển liên tục trong nhiều năm mà không phải tái cấu trúc phần lõi.

* **Local-First & Privacy-First**: Ưu tiên xử lý dữ liệu và lưu trữ bộ nhớ cục bộ trên máy của người dùng. Không đồng bộ hóa đám mây theo mặc định.
* **Modular Agent Architecture**: Phân tách hoàn toàn giữa bộ não tư duy (Brain) và các công cụ thực thi hành vi (Agents).
* **Extensibility**: Cho phép bên thứ ba dễ dàng phát triển thêm các plugin và công cụ bổ sung thông qua giao thức chuẩn hóa MCP (Model Context Protocol).

---

## 2. Features (Tính năng nổi bật)
* **Bộ nhớ dài hạn thông minh (Local Memory)**: Lưu trữ lịch sử, sự kiện, thông tin cá nhân và tri thức thông qua cơ sở dữ liệu quan hệ (SQLite) kết hợp tìm kiếm ngữ nghĩa (Vector DB).
* **Hệ thống Agent đa nhiệm (Multi-Agent System)**: Các Agent chuyên trách điều khiển trình duyệt, thao tác hệ thống Windows, xử lý tệp tin và chạy dòng lệnh.
* **Tương tác đa phương thức (Multimodal Input/Output)**: Hỗ trợ giao tiếp bằng văn bản, giọng nói (STT/TTS) và khả năng thị giác (Vision, OCR).
* **Hỗ trợ Plugin động**: Tích hợp nhanh các dịch vụ ngoài như GitHub, Discord, Spotify... thông qua hệ thống Plugin linh hoạt.

---

## 3. Architecture (Kiến trúc hệ thống)

### Nguyên tắc nền tảng (Foundation Rule)
> **Brain không được gọi trực tiếp bất kỳ Agent nào.**

Mọi yêu cầu từ người dùng đều phải đi qua một luồng dữ liệu một chiều nghiêm ngặt. Điều này giúp giảm độ liên kết (decoupling), dễ dàng thử nghiệm, và cho phép thay thế hoặc nâng cấp bất kỳ Agent nào mà không ảnh hưởng tới logic suy luận của Brain.

### Luồng xử lý hành động (Action Dispatch Flow)
```text
User (Người dùng)
   ↓
Desktop UI (Giao diện ứng dụng)
   ↓
Brain (Bộ não / Bộ suy luận)
   ↓
Planner (Bộ lập kế hoạch tác vụ)
   ↓
Action Dispatcher (Bộ điều phối hành động)
   ↓
Tool Registry (Đăng ký & Quản lý Công cụ)
   ↓
Agent (Thành phần thực thi: Browser, Windows, File...)
   ↓
Result (Kết quả thực thi trả về)
   ↓
Memory (Bộ nhớ lưu vết ngữ cảnh)
```

---

## 4. Tech Stack (Công nghệ sử dụng)
* **Core & Logic AI**: Python / Node.js (TypeScript) - Tùy thuộc vào yêu cầu hiệu năng và tính tích hợp.
* **Desktop UI & Launcher**: Electron / Tauri (HTML, CSS, TypeScript) hỗ trợ chạy nền và khởi động cùng hệ thống.
* **Local Databases**: SQLite (Dữ liệu quan hệ & Bộ nhớ ngữ cảnh) kết hợp ChromaDB / Qdrant (Bộ nhớ vector).
* **Giao thức kết nối**: Model Context Protocol (MCP) làm chuẩn giao tiếp chính giữa Server và các Agents/Tools.

---

## 5. Folder Structure (Cấu trúc thư mục)
Cấu trúc thư mục của Eric tuân theo mô hình phân rã chức năng nghiêm ngặt:

```text
Eric/
├── apps/          # Các ứng dụng chạy độc lập (desktop UI, launcher, server...)
├── core/          # Bộ não và logic AI cốt lõi (brain, planner, scheduler, events...)
├── packages/      # Thư viện dùng chung của hệ thống (shared, mcp, automation...)
├── tools/         # Các Agent và công cụ thực thi độc lập (browser-agent, file-agent...)
├── plugins/       # Các plugin mở rộng kết nối dịch vụ ngoài (github, discord...)
├── storage/       # Bộ nhớ cục bộ (memory, vector, cache, logs...)
├── resources/     # Tài nguyên tĩnh cho AI (prompts, templates, models...)
├── configs/       # Các tệp cấu hình hệ thống (app, llm, agents, voice...)
├── docs/          # Tài liệu đặc tả kỹ thuật và thiết kế
├── tests/         # Hệ thống kiểm thử tự động (unit, integration, agent)
├── scripts/       # Script dùng để build, setup và tự động hóa
└── assets/        # Icon, hình ảnh, âm thanh giao diện
```

---

## 6. Installation (Cài đặt)
*(Sẽ được cập nhật chi tiết khi bước vào Phase 2)*
1. Cài đặt các công cụ phụ thuộc: Node.js (>= 18), Python (>= 3.10), Git.
2. Clone repository về máy cá nhân:
   ```bash
   git clone https://github.com/your-repo/eric.git
   cd eric
   ```
3. Chạy script cài đặt môi trường ban đầu:
   ```bash
   npm run setup  # Hoặc script tương đương tùy cấu hình hệ thống
   ```

---

## 7. Development (Phát triển)
* **Quy tắc Git Branch**:
  * `main`: Chỉ chứa các bản phát hành ổn định (stable release). Không commit trực tiếp lên main.
  * `develop`: Nhánh tích hợp các tính năng mới cho chu kỳ phát hành tiếp theo.
  * `feature/*`: Nhánh phát triển tính năng cụ thể hoặc Agent mới, được merge vào `develop` qua Pull Request.
* **Quy chuẩn Code**: Xem chi tiết tại [Coding-Convention.md](file:///D:/Projects/Eric/docs/Coding-Convention.md).

---

## 8. Roadmap (Lộ trình phát triển)
* **Phase 0 (Chuẩn bị)**: Thiết lập cấu trúc thư mục, quy tắc Git, quy chuẩn coding, và tài liệu hóa thiết kế hệ thống.
* **Phase 1 (Nền tảng)**: Xây dựng hệ thống cấu hình, Event Bus, Dependency Injection, Logger, và Plugin Loader.
* **Phase 2 (Giao diện)**: Phát triển ứng dụng Desktop UI, Launcher khởi động cùng Windows và thanh khay hệ thống (System Tray).
* **Phase 3 (Trí tuệ cốt lõi)**: Thiết lập Brain, quản lý Context, hệ thống Prompt và Memory dài/ngắn hạn.
* **Phase 4 (Agents thực thi)**: Xây dựng Browser Agent (CDP, điều khiển tab), Windows Agent (thao tác OS), File Agent và Terminal Agent.
* **Phase 5 (Khả năng suy luận nâng cao)**: Tích hợp bộ lập lịch Planner, Reasoner sâu, Multi-Agent phối hợp và cơ chế tự phản hồi (Reflection).
* **Phase 6 (Tương tác nâng cao)**: Bổ sung giọng nói (Voice), Thị giác (Vision, OCR, Camera) và Tự động hóa quy trình phức tạp.

Chi tiết xem tại [Roadmap.md](file:///D:/Projects/Eric/docs/Roadmap.md).

---

## 9. License (Giấy phép)
Dự án được phân phối dưới giấy phép **MIT License**. Xem thêm chi tiết tại tệp [LICENSE](file:///D:/Projects/Eric/LICENSE).
