# Đặc tả Các Tác nhân Thực thi (Agents Specification)

Tài liệu này đặc tả thiết kế chi tiết và các giao diện lập trình của các Agent nằm trong thư mục `tools/`.

## Nội dung sẽ phát triển:
1. **Kiến trúc chung của một Agent**: Cách thức đóng gói một tác nhân thực thi độc lập (đầu vào, đầu ra, quản lý trạng thái nội bộ).
2. **Quy chuẩn giao tiếp**: Cách đăng ký các hành động của Agent dưới dạng các Tools vào `Action Dispatcher`.
3. **Các Agent Core**:
   * **Browser Agent**: Duyệt web, xử lý tab, chụp màn hình.
   * **Windows Agent**: Mô phỏng chuột, bàn phím, điều khiển cửa sổ.
   * **File Agent**: Tạo, đọc, cập nhật, xóa file an toàn.
   * **Terminal Agent**: Thực thi CMD/PowerShell trong sandbox.
