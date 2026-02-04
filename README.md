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
2. click đúp vào file `login.html` (hoặc `index.html`) để mở trong trình duyệt.

## Chạy trên GitHub Codespaces

Dự án này đã được cấu hình sẵn để chạy trên GitHub Codespaces với file `.devcontainer/devcontainer.json`.

### Bước 1: Tạo Codespace
1. Truy cập: **https://github.com/Ngocmai242/Fitting-AI-**
2. Nhấn vào nút **Code** (màu xanh lá cây).
3. Chọn tab **Codespaces**.
4. Nhấn **Create codespace on main** (hoặc **Open** nếu đã có Codespace).
5. Đợi khoảng 1-2 phút để môi trường khởi tạo.

### Bước 2: Khởi động Backend
Khi Codespace đã mở xong, trong **Terminal** (Ctrl + ` hoặc View → Terminal), chạy:

```bash
# Cấp quyền thực thi cho script
chmod +x start.sh

# Chạy backend server
./start.sh
```

**HOẶC** chạy trực tiếp:
```bash
python backend/run.py
```

**Lưu ý:** Backend sẽ chạy ở port **5050**. Bạn sẽ thấy thông báo:
```
>>> Starting AuraFit Server on Port 5050...
```

### Bước 3: Mở Frontend với Live Server
1. Trong Explorer sidebar bên trái, mở file **`frontend/login.html`** hoặc **`frontend/index.html`**.
2. Click chuột phải vào file → chọn **"Open with Live Server"**.
3. **HOẶC** nhấn nút **"Go Live"** ở thanh status bar (góc dưới phải màn hình).

Live Server sẽ tự động mở frontend trong một **Simple Browser** hoặc tab mới.

### Bước 4: Port Forwarding
GitHub Codespaces sẽ tự động forward ports:
- **Port 5050** - Backend API
- **Port 5500** - Live Server (Frontend)

Nếu có popup "A service is available on port...", nhấn **Open in Browser**.

### Khắc phục lỗi
**Lỗi: `python: can't open file 'backend/app.py'`**
- ✅ **Giải pháp:** Chạy `python backend/run.py` thay vì `backend/app.py`

**Lỗi: CORS hoặc không kết nối được API**
- ✅ **Đã được sửa:** Code tự động phát hiện môi trường Codespaces và cho phép CORS.
- Nếu vẫn lỗi, thử rebuild container: `Ctrl+Shift+P` → **"Codespaces: Rebuild Container"**

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
