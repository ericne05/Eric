# ENGINEERING GUIDE — Triết Lý Lập Trình & Quy Chuẩn Kỹ Thuật

> **Hướng Dẫn Kỹ Thuật Dự Án Eric**  
> Định hình phong cách lập trình, chiến lược kiểm thử và tư duy thiết kế cho toàn bộ hệ thống.

---

## 💡 1. Triết Lý Lập Trình (Coding Philosophy)

1. **Ưu tiên Composition hơn Inheritance (Prefer Composition over Inheritance)**:
   Hạn chế việc thừa kế sâu nhiều lớp. Sử dụng Interface/Abstract Class kết hợp với Composition để lắp ráp tính năng linh hoạt.

2. **Mô-đun Nhỏ & Hàm Thuần (Small Modules & Pure Functions)**:
   Mỗi file nên nằm dưới 300 LOC. Mỗi hàm chỉ làm duy nhất một việc và hạn chế tối đa side-effects không mong muốn.

3. **Tiêm Phụ Thuộc (Dependency Injection - DI)**:
   Truyền dependencies qua constructor (`__init__`) thay vì khởi tạo cứng bên trong class. Điều này giúp code cực kỳ dễ test và mock.

4. **Không Dùng Biến Toàn Cục (No Global Variables)**:
   Hạn chế tối đa biến global. State của ứng dụng phải do Kernel, Memory Manager hoặc Config Loader quản lý.

5. **Không Dùng Singleton Cứng (No Hard Singletons)**:
   Trừ các trường hợp ADR quy định rõ, các class nên được khởi tạo qua DI Container hoặc Factory để có thể khởi tạo nhiều instance độc lập trong Unit Tests.

6. **An Toàn Kiểu Dữ Liệu (Type Safety)**:
   100% type hints cho mọi hàm và phương thức. Sử dụng Dataclasses hoặc NamedTuples để đóng gói dữ liệu có cấu trúc.

---

## 🧪 2. Chiến Lược Kiểm Thử (Testing Strategy)

Hệ thống testing của Eric chia thành 4 cấp độ:

```
                  ┌──────────────────────┐
                  │    Benchmark / Perf  │
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │      Agent E2E       │
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │   Integration Test   │
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │     Unit Test        │
                  └──────────────────────┘
```

1. **Unit Tests (`tests/unit/`)**:
   - Kiểm thử từng class, function độc lập.
   - Thư viện: `pytest`.
   - Mock tất cả external I/O, DB, Network.
   - Thời gian chạy phải < 1 giây cho toàn bộ suite.

2. **Integration Tests (`tests/integration/`)**:
   - Kiểm thử sự tương tác giữa 2 hoặc nhiều module (ví dụ: Kernel + Bootstrap + EventBus + Logger).
   - Kiểm tra luồng event phát ra và nhận về.

3. **Agent E2E Tests (`tests/agents/`)**:
   - Kiểm thử các kịch bản chạy thật của Agent (ví dụ: BrowserAgent mở trang web giả lập và tương tác elements).

4. **Benchmark & Performance (`tests/benchmark/`)**:
   - Đo đạc latency xử lý tin nhắn, thời gian boot Kernel và bộ nhớ tiêu thụ.

---

## 📝 3. Format Docstrings Tiêu Chuẩn (Google Style)

Tất cả public class, method và function đều phải có docstring theo Google Format:

```python
def setup_logger(config: dict) -> ILogger:
    """
    Factory function to initialize and configure the logging subsystem.

    Redirects Python's standard `logging` to loguru and configures LoggerManager sinks.

    Args:
        config: Logging configuration dictionary containing handlers setup.

    Returns:
        Configured ILogger instance implementing the logging contract.

    Raises:
        ValueError: If config dict is malformed or missing required keys.
    """
```
