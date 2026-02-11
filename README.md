# AI Virtual Fitting & Style Recommendation Platform

Một nền tảng web Full-Stack đơn giản cho phép người dùng thử các trang phục ảo và nhận gợi ý phong cách dựa trên AI. Hệ thống sử dụng Python Flask cho backend và HTML/CSS/JS thuần cho frontend.

## Cấu trúc dự án

```
project/
├── backend/            # Python Flask App
│   ├── app.py          # Server chính
│   ├── requirements.txt # Các thư viện cần thiết
│   └── server_dev.py   # Server cho môi trường dev (auto-reload)
├── frontend/           # Giao diện người dùng
│   ├── index.html      # Trang chủ (Dashboard)
│   ├── login.html      # Trang đăng nhập
│   ├── register.html   # Trang đăng ký
│   ├── style.css       # Style Pastel Minimalism
│   └── script.js       # Logic xử lý gọi API
├── database/           # Chứa cơ sở dữ liệu SQLite
│   └── database_v2.db  # Tự động tạo khi chạy app
├── package.json        # Quản lý script chạy song song (npm start)
└── README.md           # Hướng dẫn sử dụng
```

## Yêu cầu hệ thống

- **Python 3.7+**: Để chạy Backend.
- **Node.js**: Để sử dụng `npm` quản lý các tiến trình song song.

## Hướng dẫn cài đặt và chạy (Khuyên dùng)

Đây là cách hiện đại và tiện lợi nhất, giúp chạy cả Backend và Frontend chỉ với một lệnh duy nhất, hỗ trợ tự động tải lại (auto-reload) khi sửa code.

### 1. Cài đặt

Mở terminal tại thư mục gốc của dự án và chạy các lệnh sau:

```bash
# 1. Cài đặt thư viện Python (Backend)
pip install -r backend/requirements.txt

# 2. Cài đặt thư viện Node.js (để chạy song song)
npm install
```

### 2. Khởi động dự án

Chỉ cần chạy một lệnh duy nhất:

```bash
npm start
```

Lệnh này sẽ:
1.  Khởi động **Backend** (Python Flask) tại `http://localhost:8080`.
    *   *Chế độ Debug được bật: Server sẽ tự động khởi động lại khi bạn sửa code Python.*
2.  Khởi động **Frontend** (http-server) tại `http://localhost:5500`.
3.  Tự động mở trình duyệt mặc định và truy cập vào trang web.

---

## Hướng dẫn chạy thủ công (Cách cũ)

Nếu bạn không muốn sử dụng Node.js, bạn có thể chạy thủ công từng thành phần:

1.  **Chạy Backend**:
    *   Mở terminal, chạy: `python backend/server.py`
    *   Server chạy tại: `http://localhost:8080`
2.  **Chạy Frontend**:
    *   Mở file `frontend/admin_login.html` (hoặc các file .html khác) trực tiếp bằng trình duyệt hoặc dùng Live Server của VSCode.

## Chức năng

### User Website:
- **Đăng ký/Đăng nhập**: Tạo tài khoản an toàn.
- **AI Try-On**: Giả lập thử đồ.
- **Gợi ý Outfit**: Xem danh sách các bộ đồ được đề xuất.

### Admin Website:
- **Đăng nhập**: Truy cập với tài khoản có quyền Admin.
- **Dashboard**: Quản lý người dùng, sản phẩm.

## Tài khoản Demo
- **User**: Đăng ký mới bất kỳ.
- **Admin**:
    - Username: `admin`
    - Password: `admin`
