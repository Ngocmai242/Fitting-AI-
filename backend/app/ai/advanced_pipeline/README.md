# AuraFit Advanced AI Pipeline

Hệ thống phân tích hình thể chuyên sâu và tìm kiếm sản phẩm thông minh, hoạt động như một microservice hỗ trợ cho dự án AuraFit.

## 1. Cơ chế hoạt động
Dự án vận hành theo mô hình hai server (Dual-Server):
*   **Main Server (Cổng 8080)**: Xử lý logic nghiệp vụ, giao diện người dùng và database.
*   **AI Service (Cổng 5000)**: Xử lý các tác vụ AI nặng (Phân loại dáng người, đo 3D).

Khi người dùng chọn chế độ "Advanced Analysis", Main Server sẽ gửi yêu cầu sang AI Service để lấy dữ liệu phân tích chuyên sâu.

## 2. Hướng dẫn khởi chạy (NPM Workflow)

### Bước 1: Cài đặt (Installation)
Chạy lệnh cài đặt tại thư mục gốc:
```bash
npm install
```
Và đảm bảo máy đã cài các thư viện Python:
```bash
pip install -r backend/app/ai/advanced_pipeline/requirements.txt
```

### Bước 2: Chạy hệ thống
Để hệ thống hoạt động đầy đủ tính năng, bạn cần chạy đồng thời cả 2 server:

1.  **Khởi động Main App**:
    ```bash
    npm start
    ```
2.  **Khởi động AI Service**:
    Mở một terminal mới và chạy:
    ```bash
    python backend/app/ai/advanced_pipeline/pipeline.py
    ```

> **Mẹo (Pro Tip):** Bạn có thể thêm `"ai": "python backend/app/ai/advanced_pipeline/pipeline.py"` vào mục `scripts` trong file `package.json` gốc, sau đó sửa lệnh `start` thành `concurrently \"npm run backend\" \"npm run ai\" \"npm run open\"` để chỉ cần 1 lệnh `npm start` là bật được tất cả.

## 3. Cấu trúc Module AI
-   `classifier.py`: Nhận diện giới tính và dáng người.
-   `smpl_engine.py`: Tái tạo 3D và tính toán số đo.
-   `vector_search.py`: Tìm kiếm sản phẩm thông minh bằng Vector.
-   `pipeline.py`: Main Service hỗ trợ cổng 5000.

## 4. Kiểm tra tích hợp
Sau khi bật cả 2 server, bạn có thể kiểm tra kết nối tại:
`GET http://localhost:8080` (Giao diện chính)
`POST http://localhost:5000/api/ai/advanced/analyze` (API AI độc lập)
