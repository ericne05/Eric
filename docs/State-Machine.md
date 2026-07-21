# Quản lý Trạng thái Ứng dụng (State Machine Specification)

Tài liệu này đặc tả các máy trạng thái (State Machines) điều khiển luồng hoạt động chính của ứng dụng Eric.

## Nội dung sẽ phát triển:
1. **Chu kỳ sống của Task (Task Lifecycle)**: Các trạng thái `Idle` -> `Planning` -> `Executing` -> `Evaluating` -> `Success` / `Failed`.
2. **Trạng thái kết nối của Trình duyệt (Browser Connection State)**: `Disconnected` -> `Launching` -> `Connected` -> `Navigating` -> `Active` -> `Closed`.
3. **Trạng thái hội thoại và suy nghĩ của Brain (Brain State)**: Trạng thái hiển thị hoạt ảnh suy nghĩ trên giao diện (Thinking, Listening, Speaking, Executing).
