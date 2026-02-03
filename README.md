# AI Virtual Fitting & Style Recommendation Platform

Một nền tảng web Full-Stack đơn giản cho phép người dùng thử các trang phục ảo và nhận gợi ý phong cách dựa trên AI. Hệ thống sử dụng Python Flask cho backend và HTML/CSS/JS thuần cho frontend.

## Cấu trúc dự án

```
project/
├── backend/            # Python Flask App
│   ├── app.py          # Server chính
│   ├── requirements.txt # Các thư viện cần thiết
├── frontend/           # Giao diện người dùng
│   ├── index.html      # Trang chủ (Dashboard)
│   ├── login.html      # Trang đăng nhập
│   ├── register.html   # Trang đăng ký
│   ├── style.css       # Style Pastel Minimalism
│   └── script.js       # Logic xử lý gọi API
├── database/           # Chứa cơ sở dữ liệu SQLite
│   └── database.db     # Tự động tạo khi chạy app
└── README.md           # Hướng dẫn sử dụng
```

## Yêu cầu

- Python 3.7+
- Trình duyệt web hiện đại (Chrome, Firefox, Edge)

## Hướng dẫn cài đặt và chạy

### 1. Chuẩn bị Backend

Mở terminal (Command Prompt hoặc PowerShell) và di chuyển vào thư mục dự án:

```bash
# Cài đặt các thư viện cần thiết
pip install -r backend/requirements.txt
```

### 2. Khởi động Server

```bash
# Chạy backend server
python backend/app.py
```

Server sẽ khởi động tại: `http://localhost:5000`

*Lưu ý: Lần chạy đầu tiên, hệ thống sẽ tự động tạo file `database.db` trong thư mục `database/`.*

### 3. Chạy Frontend

Vì frontend sử dụng HTML thuần giao tiếp với API, bạn chỉ cần mở file trực tiếp:

1. Vào thư mục `frontend`.
2. Click đúp vào file `login.html` (hoặc `index.html`) để mở trong trình duyệt.

## Chức năng

### User Website:
- **Đăng ký/Đăng nhập**: Tạo tài khoản an toàn (mật khẩu được mã hóa).
- **AI Try-On**: Giả lập thử đồ (nhấn nút "Start Virtual Try-On" trên Dashboard).
- **Gợi ý Outfit**: Xem danh sách các bộ đồ được đề xuất kèm link mua hàng.

### Admin Website:
- **Đăng nhập**: Truy cập với tài khoản có quyền Admin.
- **Dashboard**: Xem thống kê người dùng và kho dữ liệu outfit (giao diện ẩn sẽ hiện ra khi Admin đăng nhập).

## Demo Credentials
Để test nhanh, bạn có thể đăng ký một tài khoản mới.
- Nếu đăng ký username là `admin`, hệ thống sẽ tự động cấp quyền **ADMIN** (dùng cho mục đích demo).
