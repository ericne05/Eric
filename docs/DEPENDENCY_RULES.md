# DEPENDENCY RULES — Quy Tắc Phụ Thuộc Giữa Các Phân Lớp

> **Quy Tắc Import & Phân Cấp Phụ Thuộc (Dependency Inversion & Import Flow)**  
> Ngăn chặn triệt để hiện tượng Import Vòng (Circular Import) và Phụ Thuộc Ngược (Reverse Coupling).

---

## 🏗️ 1. Sơ Đồ Phân Cấp Module (Module Layer Hierarchy)

Phụ thuộc **CHỈ ĐƯỢC PHÉP ĐI TỪ TRÊN XUỐNG DƯỚI** (ngoài vào trong):

```
                  ┌──────────────────────┐
                  │    Apps / Desktop    │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │     Core::Kernel     │
                  └──────────┬───────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ Core::Event │  │ Core::Logger│  │ Core::Config│
     └─────────────┘  └─────────────┘  └─────────────┘
            ▲                ▲                ▲
            └────────────────┼────────────────┘
                             │
                  ┌──────────┴───────────┐
                  │   Brain / Planner    │
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │  Action Dispatcher   │
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │   Tool Registry      │
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │   Agents / Tools     │
                  └──────────────────────┘
```

---

## ✅ 2. Các Luồng Import Được Cho Phép (Allowed Imports)

- **`Kernel`** -> được phép import `ILogger`, `EventBus`, `ConfigLoader`, `DIContainer`, `ServiceRegistry`, `PluginLoader`.
- **`Brain / Planner`** -> được phép import `Event`, `EventBus`, `ILogger`, `ContextManager`, `Memory`.
- **`Action Dispatcher`** -> được phép import `Event`, `EventBus`, `ILogger`, `ToolRegistry`.
- **`Agents`** -> được phép import `Event`, `EventBus`, `ILogger`, `ToolSchema`.

---

## ❌ 3. Các Luồng Import Bị CẤM (Forbidden Imports)

- 🚫 **`Logger` -> `EventBus`**: Logger KHÔNG ĐƯỢC import hay publish Event lên EventBus (Tránh vòng lặp Event -> Logger -> Event).
- 🚫 **`EventBus` -> `Logger`**: EventBus KHÔNG ĐƯỢC phụ thuộc vào Logger cụ thể.
- 🚫 **`Logger` -> `Kernel`**: Module con KHÔNG ĐƯỢC import Kernel.
- 🚫 **`Brain` -> `Agent Implementations`**: Brain KHÔNG ĐƯỢC import mã nguồn của BrowserAgent, WindowsAgent hay FileAgent.
- 🚫 **`Agent` -> `Agent`**: BrowserAgent KHÔNG ĐƯỢC import WindowsAgent hoặc FileAgent.
- 🚫 **`Memory` -> `UI`**: Storage/Memory KHÔNG ĐƯỢC import bất kỳ component nào của Desktop UI.

---

## 🔍 4. Thứ Tự Import Tiêu Chuẩn Trong Mỗi File Python

1. Standard library imports (e.g., `os`, `sys`, `pathlib`, `typing`, `uuid`)
2. Third-party library imports (e.g., `pyyaml`, `loguru`, `dotenv`, `pytest`)
3. Local application imports (e.g., `core.events`, `core.logger`, `core.kernel`)
