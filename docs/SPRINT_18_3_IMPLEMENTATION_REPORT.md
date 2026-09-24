# SPRINT 18.3 — WINDOWS COMPANION LIFECYCLE IMPLEMENTATION REPORT

**Project:** Eric — Windows 11 AI Desktop Assistant  
**Repository Path:** `D:\Projects\Eric`  
**Date:** 2026-09-25  
**Baseline Commit:** `9795701`  
**Sprint:** 18.3 — Windows Companion Lifecycle  
**Status:** ✅ Completed  

---

## 1. Executive Summary

Sprint 18.3 transforms Eric into a true Windows companion application with an authoritative lifecycle coordinator (`CompanionApplication`) that operates without requiring a full GUI framework yet.

Key achievements:
- **Single-Instance Mutex:** Native Win32 Named Mutex (`Local\EricDesktopAssistant_SingleInstance_Mutex`) prevents duplicate companion processes.
- **System Tray Lifecycle:** System tray integration via `pystray` and `Pillow`, featuring non-blocking background threads, automatic status badges, and testable mock seams.
- **Strict Hide vs. Quit Separation:**
  - Closing the UI window hides the presentation host while keeping Eric's runtime and tray alive.
  - Quitting from the system tray executes an authoritative shutdown sequence: hiding presentation -> stopping tray -> stopping EricClient (stopping RuntimeHost and Kernel) -> releasing the mutex lock.
- **Deterministic Startup Recovery:** If runtime or tray initialization fails, already-acquired resources are deterministically rolled back in reverse order, ensuring no dangling mutex locks or orphan threads.
- **Autostart Abstraction:** Added `IStartupManager` and `WindowsStartupManager` (targeting `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`), with default-disabled behavior and mock test seams to safeguard developer registries.

---

## 2. Architecture & Design

### 2.1 Companion Application Lifecycle Topology
```text
                    Windows OS / Taskbar Tray / User Actions
                                      │
                                      ▼
                        CompanionApplication (Coordinator)
                         ├── ISingleInstanceLock (Named Mutex)
                         ├── ITrayManager (pystray)
                         ├── IPresentationHost (Show / Hide)
                         └── IStartupManager (Windows Registry)
                                      │
                                      ▼
                           EricClient (Client Boundary)
                                      │
                                      ▼
                         IEricRuntime (Host Interface)
                                      │
                                      ▼
                        EricRuntimeHost (Authoritative Host)
                                      │
                                      ▼
                               Kernel / Engine
```

### 2.2 Strict Component Encapsulation
`CompanionApplication` interacts with the backend engine **exclusively through `EricClient`**. It has zero knowledge of `Kernel`, `Container`, `GoalManager`, `EventBus`, `LLMRouter`, `DesktopRuntime`, or `VisionRuntime`.

---

## 3. Key Components Implemented

### 3.1 Single-Instance Enforcement (`app/platform/single_instance.py`)
- **`WindowsSingleInstanceLock`:**
  - Uses Win32 `CreateMutexW` via `ctypes.windll.kernel32`.
  - Mutex identifier: `Local\EricDesktopAssistant_SingleInstance_Mutex`.
  - Detects duplicate processes via Win32 error `ERROR_ALREADY_EXISTS` (`183`).
  - Ensures clean handle closing via `CloseHandle` upon application exit.
- **`MockSingleInstanceLock`:**
  - In-memory mock providing deterministic acquire/release tracking for unit tests.

### 3.2 System Tray Management (`app/platform/tray.py`)
- **`PystrayTrayManager`:**
  - Production Windows system tray implementation using `pystray` and `Pillow`.
  - Runs detached on a background thread (`run_detached()`) so the asyncio event loop remains non-blocking.
  - Dynamically builds the menu:
    - `"Eric AI Assistant"` (Header)
    - `"Open Eric"` (Triggers `presentation.show()`)
    - `"Status: <READY/BUSY/ERROR>"` (Displays live status)
    - `"Quit Eric"` (Triggers `companion.quit()`)
- **`MockTrayManager`:**
  - Headless test seam simulating tray events (`simulate_open()`, `simulate_quit()`) without requiring an OS display or mouse interaction.

### 3.3 Presentation Host Abstraction (`app/platform/presentation.py`)
- **`IPresentationHost`:**
  - Defines `show()`, `hide()`, and `is_visible() -> bool`.
- **`MockPresentationHost`:**
  - Emulates window visibility and captures `request_close()` events.
- **`EricDesktopClient` Integration:**
  - Updated `EricDesktopClient` in `app/main.py` to directly satisfy `IPresentationHost`.

### 3.4 Autostart Management (`app/platform/startup.py`)
- **`WindowsStartupManager`:**
  - Manages Windows autostart under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
  - Distinguishes frozen PyInstaller executable (`sys.executable`) from source-based development runs (`sys.executable main.py`).
  - **Safety constraint:** Disabled by default during development and tests.
- **`MockStartupManager`:**
  - In-memory mock ensuring zero registry mutations during test execution.

### 3.5 Companion Application Coordinator (`app/lifecycle/companion_app.py`)
- **`start(start_hidden: bool = False) -> CompanionStartupResult`:**
  - Step 1: Acquires single-instance mutex. If another instance exists, returns immediately with `is_duplicate_instance = True`.
  - Step 2: Starts runtime via `EricClient.start()`. Rolls back mutex if startup fails.
  - Step 3: Starts system tray and wires menu callbacks. Rolls back client and mutex if tray fails.
  - Step 4: Subscribes tray to `runtime.*` events for live status synchronization.
  - Step 5: Shows presentation host unless `start_hidden=True`.
- **`quit() -> None`:**
  - Thread-safe and idempotent quit sequence:
    1. Hide presentation host.
    2. Stop system tray icon and background thread.
    3. Stop EricClient (stopping runtime runtimes and shutting down Kernel).
    4. Release single-instance mutex lock.
    5. Clean process termination without forced `os._exit()`.

---

## 4. Files Created & Modified

### Created
1. `app/platform/interfaces.py`: Protocols for `ISingleInstanceLock`, `ITrayManager`, `IPresentationHost`, `IStartupManager`.
2. `app/platform/single_instance.py`: Windows Win32 named mutex and mock locks.
3. `app/platform/tray.py`: Pystray tray manager and mock tray manager.
4. `app/platform/presentation.py`: Presentation host protocol implementation.
5. `app/platform/startup.py`: Windows registry autostart manager and mock.
6. `app/platform/__init__.py`: Package exports for `app.platform`.
7. `app/lifecycle/companion_app.py`: `CompanionApplication` lifecycle coordinator.
8. `app/lifecycle/__init__.py`: Package exports for `app.lifecycle`.
9. `tests/unit/test_sprint18_3_companion.py`: 14 unit tests covering the companion lifecycle.
10. `docs/SPRINT_18_3_IMPLEMENTATION_REPORT.md`: This report.

### Modified
1. `requirements.txt`: Added `pystray>=0.19.5`.
2. `eric.spec`: Added hidden imports for `app.client`, `app.platform`, `app.lifecycle`, and `pystray`.
3. `app/main.py`: Implemented `show()`, `hide()`, and `is_visible()` on `EricDesktopClient`.
4. `PROJECT_STATUS.md`: Updated sprint status and test suite metrics.

---

## 5. Test Suite Verification

- Sprint 18.2 Baseline: **328 passed**
- Sprint 18.3 Tests Added: **14 passed**
- Total Passing: **342 passed, 0 failed, 0 skipped**
