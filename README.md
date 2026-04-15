# Nền Tảng Thử Đồ & Gợi Ý Thời Trang AI (Fitting-AI)

## Giới Thiệu
Fitting-AI là một hệ thống web tích hợp trí tuệ nhân tạo (AI) giúp người dùng:
1. **Thử đồ ảo (Virtual Try-On)**: Ướm thử quần áo lên ảnh thật của người dùng với độ chân thực cao nhờ công nghệ AI.
2. **Gợi ý tự động (AI Style Recommendation)**: Phân tích dáng người và đưa ra gợi ý trang phục dựa trên các quy tắc thời trang chuẩn mực.

Dự án được xây dựng với kiến trúc Client-Server hiện đại, kết hợp với các mô hình Machine Learning chuyên sâu.

## Cấu Trúc Dự Án
- `/frontend/`: Giao diện người dùng (HTML, CSS Pastel Minimalism, JS thuần).
- `/backend/`: Máy chủ API điều phối toàn bộ hệ thống (Python & Flask).
- `/ai_engine/` & `/VITON-HD/`: Các lõi xử lý AI chuyên sâu (Tách nền, Thử đồ ảo - VTON, Nhận diện dáng người).
- `/data_engine/`: Hệ thống cào dữ liệu (Crawler) và tự động gắn thẻ (Tagger) quần áo.
- `/database/`: Nơi lưu trữ thông tin người dùng và sản phẩm (SQLite).

## Hướng Dẫn Cài Đặt & Chạy
Hệ thống sử dụng `npm` để quản lý và chạy đồng thời cả giao diện lẫn máy chủ một cách mượt mà.

### 1. Chuẩn Bị
Mở Terminal tại thư mục dự án và chạy:
```bash
# Cài đặt thư viện Python (Máy chủ API)
pip install -r backend/requirements.txt

# Cài đặt công cụ nền tảng Node.js (quản lý chạy song song)
npm install
```

### 2. Khởi Động
Chỉ bằng một lệnh duy nhất:
```bash
npm start
```
Lệnh này sẽ tự động:
- Khởi chạy Backend trên cổng `8080` (tích hợp Auto-reload nếu bạn sửa code).
- Phục vụ Frontend trên cùng tên miền.
- Tự động mở trình duyệt truy cập thẳng vào trang chủ web.

---

## Kiến Trúc Trí Tuệ Nhân Tạo (AI Pipeline)
Hệ thống AI của dự án bao gồm 3 trụ cột kết hợp:
- **Computer Vision (MoveNet / EfficientNet)**: Được nhúng trực tiếp để xác định các khung xương (landmarks), đo đạc tỷ lệ cơ thể và phân loại dáng người.
- **Logical Rules / Fashion LLM**: Hệ luật kết hợp mô hình ngôn ngữ (Gemma-3-4b), kết nối với kiến thức từ tệp `DeepFashion2` và `Polyvore` để đánh giá quần áo nào vừa với dáng người nào.
- **Image Generation (VITON-HD)**: Công nghệ hình ảnh đỉnh cao giúp ghép trang phục lên cơ thể người một cách mềm mại (đổ bóng chân thực, bảo toàn kết cấu vải).

## Thông Tin Chạy Thử (Demo)
- **Truy cập web**: `http://localhost:8080/index.html`
- **Tài khoản Khách**: Bấm Đăng ký ngay trên màn hình.
- **Tài khoản Admin**: 
  - Đăng nhập: `http://localhost:8080/admin_login.html`
  - Username: `admin`
  - Password: `admin`
