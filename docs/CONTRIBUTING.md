# CONTRIBUTING — Hướng Dẫn Cộng Tác Dự Án Eric

> **Dành cho AI Agents và Lập trình viên**  
> Quy trình chuẩn để đóng góp mã nguồn, kiểm thử và tạo Pull Requests cho Eric.

---

## 🛠️ Quy Trình 5 Bước Đóng Góp Code

### Step 1: Kiểm tra trạng thái hiện tại
1. Đọc `docs/HANDOFF.md` để nắm được Sprint hiện tại và Read Order.
2. Đọc `docs/CONSTITUTION.md` và `docs/DEPENDENCY_RULES.md` để đảm bảo không vi phạm luật kiến trúc.
3. Chạy `pytest tests/ -v` xác nhận toàn bộ test suite pass 100% trước khi sửa code.

### Step 2: Tạo nhánh Feature Branch
Không bao giờ commit trực tiếp trên `main` hoặc `develop`. Tạo nhánh feature mới từ `develop`:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/sprint-N-<feature-name>
```

### Step 3: Viết Code & Unit Tests
1. Tuân thủ 100% Type Hints và Google Style Docstrings (`docs/ENGINEERING_GUIDE.md`).
2. Viết Unit Tests mới trong `tests/unit/test_<module>.py`.
3. Kiểm tra coverage mục tiêu ≥90%.

### Step 4: Verification & Pre-Commit Check
Chạy toàn bộ test suite và kiểm tra không vỡ bất kỳ test cũ nào:
```bash
.venv\Scripts\pytest tests/ -v
```

### Step 5: Commit & Merge Workflow
Commit theo chuẩn **Conventional Commits**:
```bash
git add .
git commit -m "feat(core): sprint N - description of change"
git checkout develop
git merge feature/sprint-N-<feature-name>
```

---

## ✅ Pull Request / DoD Checklist

Trước khi hoàn thành công việc, đảm bảo:
- [ ] 100% Unit tests mới và cũ PASS (`pytest tests/ -v`).
- [ ] Không có dead code, no `print()` statements trong core logic.
- [ ] Không vi phạm Architecture Freeze.
- [ ] Đã cập nhật `docs/PROJECT_STATUS.md` và `docs/CHANGELOG.md`.
- [ ] Đã tạo Completion Report đúng format.
