# Đặc tả Bộ nhớ Cục bộ (Local Memory Specification)

Tài liệu này sẽ đặc tả thiết kế chi tiết cho thành phần quản lý bộ nhớ của Eric tại `core/memory` kết hợp với thư mục dữ liệu cục bộ `storage/`.

## Nội dung sẽ phát triển:
1. **Bộ nhớ hội thoại ngắn hạn (Short-term / Episodic Memory)**: Thiết kế bảng cơ sở dữ liệu SQLite lưu giữ các lượt tương tác gần đây.
2. **Bộ nhớ tri thức dài hạn (Long-term / Semantic Memory)**: Lược đồ (schema) lưu trữ facts và user profile trong SQLite.
3. **Bộ nhớ Vector (Vector Database)**: Lựa chọn vector database (ChromaDB, Qdrant...) và cấu hình mô hình Embedding (Text-embedding).
4. **Tiến trình hợp nhất bộ nhớ (Consolidation Pipeline)**: Thuật toán quét nền định kỳ để trích xuất tri thức quan trọng từ bộ nhớ ngắn hạn đưa vào bộ nhớ dài hạn và loại bỏ dữ liệu rác.
