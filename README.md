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

## 3. Architecture (Kiến trúc hệ thống v1.0 RC)

### Nguyên tắc nền tảng (Foundation Rule)
> **LLM không bao giờ trực tiếp thực thi các lệnh hệ điều hành hay shell script.**

Mọi yêu cầu từ người dùng đều phải đi qua luồng điều hướng và trừu tượng hóa nghiêm ngặt:

```text
User Input (Người dùng)
   ↓
App Shell / UI
   ↓
IntentClassifier & LLMRouter
   ↓
Structured GoalSpecification
   ↓
GoalManager & CognitiveCoordinator
   ↓
CapabilityNegotiator
   ↓
Runtime Adapters (Windows Desktop, Playwright Browser, Local Vision)
   ↓
Operating System / Browser / OCR
   ↓
Execution Result & Memory / Knowledge Graph
```

---

## 4. Tech Stack (Công nghệ sử dụng)
* **Core & Logic AI**: Python 3.10+ (Asyncio, Pydantic, YAML)
* **LLM Integration**: Google GenAI Client SDK (Gemini 2.0 Flash), OpenAI, Anthropic Claude with Multi-Provider Failover Router
* **Desktop Automation**: PyAutoGUI, Windows CTypes SendInput, win32gui, MSS Screenshot Engine
* **Browser Automation**: Async Playwright Chromium
* **Vision & OCR**: Pytesseract OCR, PIL Semantic Screen Graph
* **Local Storage & Memory**: SQLite (Long-term Memory & Knowledge Graph), FIFO Short-term Buffer, In-memory Vector Store
* **Desktop Host & Client**: Native Python Application Shell, Command Palette, Session Manager

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
