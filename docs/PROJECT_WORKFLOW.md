# 🚀 **TỔNG HỢP WORKFLOW TOÀN HỆ THỐNG VIRTUAL TRY-ON & AI PHỐI ĐỒ**

## 📋 **TỔNG QUAN HỆ THỐNG**

```
┌─────────────────────────────────────────────────────────────────┐
│                   HỆ THỐNG VIRTUAL TRY-ON AI                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐            ┌─────────────────────┐    │
│  │      PHẦN ADMIN     │            │      PHẦN USER      │    │
│  ├─────────────────────┤            ├─────────────────────┤    │
│  │ 1. Crawl Shopee     │◀──────────▶│ 1. Upload ảnh       │    │
│  │ 2. Quản lý SP       │            │ 2. AI phân tích     │    │
│  │ 3. Training AI      │   Dữ liệu  │ 3. Gợi ý outfit     │    │
│  │ 4. Quản lý outfit   │            │ 4. Virtual Try-On   │    │
│  │ 5. Dashboard        │            │ 5. Mua hàng         │    │
│  └─────────────────────┘            └─────────────────────┘    │
│           │                               │                     │
│           └─────────────┬─────────────────┘                     │
│                         ▼                                       │
│               ┌─────────────────┐                               │
│               │   DATABASE &    │                               │
│               │   AI MODELS     │                               │
│               └─────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 **PHẦN ADMIN - FULL WORKFLOW**

### **WORKFLOW 1: CRAWL DỮ LIỆU TỪ SHOPEE**

**📎 Flow kỹ thuật chuẩn (Browser + Intercept JSON):** [SHOPEE_CRAWL_FLOW.md](SHOPEE_CRAWL_FLOW.md)

```
┌─────────────────────────────────────────────────────────────┐
│               WORKFLOW CRAWL SHOPEE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [START]                                                    │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 1: Admin nhập link cửa hàng Shopee             │   │
│  │ - Giao diện form nhập link                          │   │
│  │ - Validate link format                              │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2: Hệ thống truy cập Shopee (xem SHOPEE_      │   │
│  │         CRAWL_FLOW.md)                              │   │
│  │ - Playwright: mở shop như user thật                 │   │
│  │ - Intercept JSON (get_shop_base_v2, search_items,  │   │
│  │   item/get) — không parse HTML, không reverse API  │   │
│  │ - Pagination: scroll / search_items offset         │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 3: Crawl danh sách sản phẩm                    │   │
│  │ - Extract product links từ trang shop               │   │
│  │ - Lưu danh sách link vào queue                      │   │
│  │ - Hiển thị progress                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 4: Crawl chi tiết từng sản phẩm                │   │
│  │ Với mỗi product link:                               │   │
│  │  - Lấy tên sản phẩm                                 │   │
│  │  - Lấy ảnh sản phẩm (tải về server)                │   │
│  │  - Lấy giá                                          │   │
│  │  - Lấy mô tả                                        │   │
│  │  - Lấy shop info                                    │   │
│  │  - Lưu link gốc                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 5: Xử lý ảnh và metadata                      │   │
│  │  - Resize ảnh về kích thước chuẩn                  │   │
│  │  - Remove background tự động                       │   │
│  │  - Đặt tên ảnh theo format:                       │   │
│  │    [shop_id]_[product_id]_[timestamp].jpg         │   │
│  │  - Extract màu sắc chính từ ảnh                   │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 6: Phân loại tự động                          │   │
│  │ Sử dụng AI/rule để phân loại:                      │   │
│  │  - Category: áo/quần/váy/phụ kiện                  │   │
│  │  - Sub-category: áo thun/sơ mi/quần jean           │   │
│  │  - Style: casual/formal/sport                      │   │
│  │  - Màu sắc chính                                   │   │
│  │  - Phù hợp body type nào                           │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 7: Lưu vào database                           │   │
│  │ Table: products                                     │   │
│  │ Columns:                                           │   │
│  │  - id, name, image_path, shopee_link, price        │   │
│  │  - category, sub_category, style, color            │   │
│  │  - body_type_suitable, gender                      │   │
│  │  - crawl_date, is_active                          │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 8: Thông báo kết quả                          │   │
│  │  - Hiển thị số lượng SP đã crawl                   │   │
│  │  - Hiển thị lỗi (nếu có)                           │   │
│  │  - Gửi notification cho admin                      │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  [COMPLETE]                                                 │
└─────────────────────────────────────────────────────────────┘
```

### **WORKFLOW 2: TRAINING AI PHỐI ĐỒ**

```
┌─────────────────────────────────────────────────────────────┐
│            WORKFLOW TRAINING AI PHỐI ĐỒ                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [START TRAINING]                                           │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GIAI ĐOẠN 1: CHUẨN BỊ DỮ LIỆU                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Bước 1.1: Thu thập dữ liệu từ nhiều nguồn          │   │
│  │  - Lấy SP từ database đã crawl                     │   │
│  │  - Crawl outfit mẫu từ Pinterest/Fashion sites     │   │
│  │  - Sử dụng public datasets (DeepFashion)           │   │
│  │  - Admin tạo outfit mẫu thủ công                   │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 1.2: Gán nhãn dữ liệu                         │   │
│  │  - Positive pairs: Outfit đẹp, hợp thời trang      │   │
│  │  - Negative pairs: Outfit không hợp                │   │
│  │  - Gán nhãn tự động + thủ công                    │   │
│  │  - Tạo file dataset:                              │   │
│  │    [top_id, bottom_id, label, style, occasion]     │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 1.3: Tiền xử lý ảnh                          │   │
│  │  - Resize ảnh về 224x224                          │   │
│  │  - Normalize pixel values                         │   │
│  │  - Data augmentation:                             │   │
│  │    • Rotation, flip                               │   │
│  │    • Color jitter                                │   │
│  │    • Random crop                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 1.4: Trích xuất đặc trưng                     │   │
│  │  - Sử dụng pre-trained model (ResNet50)           │   │
│  │  - Extract features từ layer trước classification │   │
│  │  - Lưu feature vectors vào vector database        │   │
│  │  - Tạo metadata cho mỗi sản phẩm                  │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GIAI ĐOẠN 2: XÂY DỰNG VÀ TRAINING MODEL            │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Bước 2.1: Chọn kiến trúc model                     │   │
│  │ Options:                                           │   │
│  │  1. Siamese Network                                │   │
│  │  2. Transformer-based                              │   │
│  │  3. Multi-modal CNN                               │   │
│  │  4. Graph Neural Network                          │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2.2: Thiết kế model (ví dụ Siamese)          │   │
│  │  Input:                                            │   │
│  │    - Top image features (512-dim)                 │   │
│  │    - Bottom image features (512-dim)              │   │
│  │    - Metadata (category, color, style)            │   │
│  │  Architecture:                                     │   │
│  │    - Two identical CNN branches                   │   │
│  │    - Concatenation layer                         │   │
│  │    - Fully connected layers (256, 128, 64)       │   │
│  │    - Output: compatibility score (0-1)           │   │
│  │  Loss: Binary Cross-Entropy                      │   │
│  │  Optimizer: Adam                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2.3: Training process                         │   │
│  │  - Split data: 70% train, 15% val, 15% test       │   │
│  │  - Batch size: 32                                 │   │
│  │  - Epochs: 100                                    │   │
│  │  - Learning rate: 0.001 với scheduler            │   │
│  │  - Early stopping khi val loss không giảm         │   │
│  │  - Sử dụng GPU acceleration                       │   │
│  │  - Log metrics với TensorBoard                    │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2.4: Đánh giá model                           │   │
│  │ Metrics:                                           │   │
│  │  - Accuracy, Precision, Recall, F1-score          │   │
│  │  - AUC-ROC curve                                  │   │
│  │  - Confusion matrix                               │   │
│  │  - Human evaluation với chuyên gia                │   │
│  │  - A/B testing với rule-based system              │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2.5: Fine-tuning & Optimization               │   │
│  │  - Hyperparameter tuning                          │   │
│  │  - Transfer learning từ fashion-specific model    │   │
│  │  - Ensemble multiple models                       │   │
│  │  - Optimize for inference speed                   │   │
│  │  - Quantization/pruning cho mobile deployment     │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GIAI ĐOẠN 3: TRIỂN KHAI MODEL                      │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Bước 3.1: Export model                             │   │
│  │  - Save model weights                             │   │
│  │  - Export thành format phù hợp (ONNX, TensorRT)   │   │
│  │  - Tạo model metadata và versioning               │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 3.2: Xây dựng AI Service API                  │   │
│  │ Endpoints:                                         │   │
│  │  - POST /api/ai/recommend-outfits                 │   │
│  │  - POST /api/ai/outfit-compatibility              │   │
│  │  - POST /api/ai/suggest-accessories               │   │
│  │  - GET  /api/ai/model-info                        │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 3.3: Integration với hệ thống chính           │   │
│  │  - Kết nối database                               │   │
│  │  - Setup caching (Redis)                          │   │
│  │  - Load balancing cho AI service                  │   │
│  │  - Monitoring với Prometheus/Grafana              │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ GIAI ĐOẠN 4: CONTINUOUS LEARNING                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Bước 4.1: Thu thập feedback                        │   │
│  │  - Log user interactions                          │   │
│  │  - Collect explicit ratings                       │   │
│  │  - Track conversion rates                         │   │
│  │  - A/B testing results                            │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 4.2: Retraining pipeline                      │   │
│  │  - Scheduled retraining (weekly/monthly)          │   │
│  │  - Trigger-based retraining khi có đủ data mới    │   │
│  │  - Version control cho model                      │   │
│  │  - Rollback capability                            │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  [TRAINING COMPLETE]                                       │
└─────────────────────────────────────────────────────────────┘
```

### **WORKFLOW 3: TẠO VÀ QUẢN LÝ OUTFIT**

```
┌─────────────────────────────────────────────────────────────┐
│           WORKFLOW TẠO OUTFIT TỰ ĐỘNG & THỦ CÔNG          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [START CREATE OUTFIT]                                      │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Option A: Tạo outfit thủ công                      │   │
│  │ 1. Chọn category (top/bottom/dress)                │   │
│  │ 2. Browse sản phẩm từ database                     │   │
│  │ 3. Drag & drop items vào outfit builder            │   │
│  │ 4. Gán metadata:                                   │   │
│  │    - Tên outfit                                    │   │
│  │    - Body type phù hợp                             │   │
│  │    - Style (casual, formal, etc.)                  │   │
│  │    - Occasion                                      │   │
│  │ 5. Lưu outfit                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Option B: Tạo outfit tự động bằng AI               │   │
│  │ 1. Chọn base item (ví dụ: một cái áo)              │   │
│  │ 2. AI gợi ý các items phù hợp:                     │   │
│  │    - Dựa trên color compatibility                  │   │
│  │    - Dựa trên style matching                       │   │
│  │    - Dựa trên outfit patterns học được            │   │
│  │ 3. Admin review và chỉnh sửa                      │   │
│  │ 4. Lưu outfit vào database                        │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Lưu trữ outfit trong database:                     │   │
│  │ Table: outfits                                      │   │
│  │ Columns:                                           │   │
│  │  - outfit_id, outfit_name                         │   │
│  │  - top_id, bottom_id, dress_id, accessory_ids     │   │
│  │  - style, body_type, occasion                     │   │
│  │  - created_by, created_at                         │   │
│  │  - ai_generated (boolean)                         │   │
│  │  - rating, popularity_score                       │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  [OUTFIT CREATED]                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 👤 **PHẦN USER - FULL WORKFLOW**

### **WORKFLOW 4: USER TRẢI NGHIỆM VIRTUAL TRY-ON**

```
┌─────────────────────────────────────────────────────────────┐
│           WORKFLOW USER VIRTUAL TRY-ON                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [USER ACCESS WEBSITE]                                      │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 1: Upload ảnh người dùng                       │   │
│  │  - Upload ảnh toàn thân                             │   │
│  │  - Yêu cầu: rõ nét, đứng thẳng, background đơn giản │   │
│  │  - Hoặc sử dụng webcam chụp ảnh                     │   │
│  │  - Validate ảnh (kích thước, định dạng)             │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2: AI Body Analysis                            │   │
│  │  Sử dụng pose estimation model (OpenPose/HRNet):    │   │
│  │  1. Detect body keypoints (17-25 points)            │   │
│  │  2. Estimate body measurements:                     │   │
│  │     - Shoulder width                                │   │
│  │     - Chest/Bust                                    │   │
│  │     - Waist                                         │   │
│  │     - Hip                                           │   │
│  │  3. Phân loại body type:                           │   │
│  │     - Apple (A)                                     │   │
│  │     - Triangle (V)                                  │   │
│  │     - Rectangle (H)                                 │   │
│  │     - Hourglass (X)                                 │   │
│  │  4. Detect gender từ hình dáng cơ thể              │   │
│  │  5. Lưu kết quả phân tích vào session              │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 3: Chọn style preference                       │   │
│  │  - Casual, Formal, Sporty, Bohemian, Streetwear     │   │
│  │  - Occasion: work, party, date, everyday           │   │
│  │  - Color preference (optional)                      │   │
│  │  - Budget range (optional)                          │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 4: AI Recommendation Engine                   │   │
│  │  1. Query database lấy sản phẩm phù hợp:           │   │
│  │     - WHERE body_type_suitable = user_body_type    │   │
│  │     - AND gender = user_gender                     │   │
│  │     - AND style = user_preferred_style             │   │
│  │  2. AI phối đồ tự động:                           │   │
│  │     - Lấy top N áo phù hợp                        │   │
│  │     - Với mỗi áo, tìm bottom phù hợp bằng model AI │   │
│  │     - Tính compatibility score                    │   │
│  │     - Sort theo score descending                  │   │
│  │  3. Trả về top 10 outfits                         │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 5: Hiển thị outfits recommendations           │   │
│  │  - Grid view các outfits                           │   │
│  │  - Mỗi outfit hiển thị:                           │   │
│  │     • Ảnh phối đồ (ảnh render)                    │   │
│  │     • Tên các items trong outfit                   │   │
│  │     • Total price                                 │   │
│  │     • Compatibility score                         │   │
│  │     • Nút "Thử đồ"                               │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 6: Virtual Try-On                             │   │
│  │  Khi user click "Thử đồ":                          │   │
│  │  1. Load ảnh người dùng và ảnh sản phẩm            │   │
│  │  2. Sử dụng Virtual Try-On AI model:               │   │
│  │     - CP-VTON, DCTON, hoặc custom model            │   │
│  │     - Warp sản phẩm theo pose người                │   │
│  │     - Blend màu sắc tự nhiên                       │   │
│  │     - Xử lý occlusion (che khuất)                  │   │
│  │  3. Hiển thị kết quả thử đồ                        │   │
│  │  4. Options:                                       │   │
│  │     - Thay đổi màu sản phẩm                       │   │
│  │     - So sánh nhiều outfits                       │   │
│  │     - Lưu ảnh thử đồ                             │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 7: Mua hàng                                   │   │
│  │  Khi user click vào sản phẩm:                      │   │
│  │  1. Hiện modal chi tiết sản phẩm                   │   │
│  │     - Ảnh sản phẩm gốc                            │   │
│  │     - Tên, giá, mô tả                             │   │
│  │     - Link Shopee gốc                             │   │
│  │     - Nút "Mua ngay"                               │   │
│  │  2. Khi click "Mua ngay":                          │   │
│  │     - Mở link Shopee trong tab mới                │   │
│  │     - Log click event để tracking                 │   │
│  │     - Cập nhật popularity score                   │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 8: Feedback & Personalization                 │   │
│  │  - User có thể rating outfit                      │   │
│  │  - Save outfit yêu thích                          │   │
│  │  - Share kết quả thử đồ                           │   │
│  │  - Dữ liệu feedback dùng để retraining AI         │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  [SESSION COMPLETE]                                        │
└─────────────────────────────────────────────────────────────┘
```

### **WORKFLOW 5: AI VIRTUAL TRY-ON REAL-TIME**

```
┌─────────────────────────────────────────────────────────────┐
│         VIRTUAL TRY-ON AI PROCESSING                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: Ảnh người + Ảnh sản phẩm                           │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 1: Pose Estimation                            │   │
│  │  - Detect body keypoints từ ảnh người              │   │
│  │  - Tạo pose map (18 channels)                      │   │
│  │  - Estimate body segmentation                      │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 2: Garment Processing                         │   │
│  │  - Remove background ảnh sản phẩm                  │   │
│  │  - Tạo mask cho sản phẩm                           │   │
│  │  - Xác định garment category (top/bottom/dress)    │   │
│  │  - Warp garment theo template                      │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 3: Geometric Matching                         │   │
│  │  - Tính thin plate spline transformation           │   │
│  │  - Warp garment cho phù hợp với body pose          │   │
│  │  - Adjust kích thước theo body measurements        │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 4: Try-On Synthesis                           │   │
│  │  - Sử dụng generator network (U-Net based)         │   │
│  │  - Input:                                          │   │
│  │     • Ảnh người                                    │   │
│  │     • Warped garment                               │   │
│  │     • Pose map                                     │   │
│  │     • Body mask                                    │   │
│  │  - Output: Ảnh người mặc đồ                        │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bước 5: Post-processing                            │   │
│  │  - Color adjustment                               │   │
│  │  - Lighting consistency                           │   │
│  │  - Edge blending                                  │   │
│  │  - Background preservation/removal                │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                       │
│     ▼                                                       │
│  Output: Ảnh người đã thử đồ                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗃️ **DATABASE ARCHITECTURE**

### **Tables Structure:**

```
1. products
   ├── id (PK)
   ├── name
   ├── image_path
   ├── shopee_link
   ├── price
   ├── category (top/bottom/dress/accessory)
   ├── sub_category
   ├── style
   ├── color
   ├── body_type_suitable (JSON: ['A','V','H','X'])
   ├── gender
   ├── shop_name
   ├── crawl_date
   ├── is_active
   └── feature_vector (BLOB)

2. outfits
   ├── id (PK)
   ├── name
   ├── top_id (FK)
   ├── bottom_id (FK)
   ├── dress_id (FK)
   ├── accessory_ids (JSON)
   ├── style
   ├── body_type (JSON)
   ├── occasion
   ├── created_by (admin/user)
   ├── created_at
   ├── ai_generated
   ├── popularity_score
   └── average_rating

3. users
   ├── id (PK)
   ├── email
   ├── body_type
   ├── height
   ├── weight
   ├── preferred_styles (JSON)
   ├── created_at
   └── last_login

4. user_sessions
   ├── id (PK)
   ├── user_id (FK)
   ├── body_analysis_result (JSON)
   ├── tryon_history (JSON)
   ├── created_at
   └── expired_at

5. ai_models
   ├── id (PK)
   ├── model_name
   ├── model_type (outfit_recommendation/virtual_tryon)
   ├── version
   ├── model_path
   ├── accuracy
   ├── trained_date
   ├── is_active
   └── metadata (JSON)

6. click_logs
   ├── id (PK)
   ├── user_id
   ├── product_id
   ├── outfit_id
   ├── action (view/click/tryon/purchase)
   ├── timestamp
   └── session_id
```

---

## 🔄 **SYSTEM INTEGRATION WORKFLOW**

```
┌─────────────────────────────────────────────────────────────────┐
│              SYSTEM INTEGRATION & DATA FLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Frontend   │    │   Backend   │    │   AI/ML     │         │
│  │  (React/    │    │  (Flask/    │    │   Services  │         │
│  │   Vue.js)   │◀──▶│   FastAPI)  │◀──▶│  (Python)   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              Database & Storage                     │       │
│  │  ├── PostgreSQL (structured data)                   │       │
│  │  ├── Redis (caching, sessions)                      │       │
│  │  ├── MinIO/S3 (image storage)                       │       │
│  │  └── Pinecone/Weaviate (vector DB)                  │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  API Endpoints:                                                │
│  ├── /api/admin/crawl           (POST) Crawl Shopee           │
│  ├── /api/admin/train-ai        (POST) Train AI model         │
│  ├── /api/ai/recommend-outfits  (POST) Get outfit recommendations │
│  ├── /api/ai/virtual-tryon      (POST) Virtual try-on         │
│  ├── /api/products              (GET) Get products            │
│  └── /api/users/upload-image    (POST) Upload user image      │
│                                                                 │
│  Cron Jobs/Scheduled Tasks:                                    │
│  ├── Daily: Retrain AI with new data                         │
│  ├── Hourly: Update product prices from Shopee               │
│  ├── Weekly: Generate outfit recommendations report          │
│  └── Monthly: Cleanup old data and logs                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 **MONITORING & MAINTENANCE WORKFLOW**

```
┌─────────────────────────────────────────────────────────────┐
│           MONITORING & MAINTENANCE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Daily Tasks:                                              │
│  ├── Check crawl job status                               │
│  ├── Monitor AI model performance                         │
│  ├── Review user feedback                                 │
│  ├── Check system logs for errors                         │
│  └── Backup database                                      │
│                                                             │
│  Weekly Tasks:                                             │
│  ├── Update product database (remove unavailable items)   │
│  ├── Retrain AI models with new data                      │
│  ├── Generate analytics reports                           │
│  ├── Review and update outfit recommendations             │
│  └── System performance optimization                      │
│                                                             │
│  Monthly Tasks:                                            │
│  ├── Full system backup                                  │
│  ├── Security audit                                      │
│  ├── Update dependencies                                 │
│  ├── Review and update AI models                         │
│  └── Plan new features and improvements                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **KEY METRICS TO TRACK**

```
1. Crawl Metrics:
   ├── Products crawled per day
   ├── Crawl success rate
   ├── Image download success rate
   └── Data processing time

2. AI Model Metrics:
   ├── Outfit recommendation accuracy
   ├── Virtual try-on quality score
   ├── Model inference time
   ├── User satisfaction rate
   └── Click-through rate on recommendations

3. User Engagement Metrics:
   ├── Daily active users
   ├── Average session duration
   ├── Outfits tried per session
   ├── Conversion rate (try-on → click)
   └── Purchase conversion rate

4. Business Metrics:
   ├── Revenue from affiliate links
   ├── Most popular products/outfits
   ├── User retention rate
   └── Cost per acquisition
```

---

## 🚀 **DEPLOYMENT ARCHITECTURE**

```
Development → Staging → Production
     │            │          │
     └─────┬──────┴─────┬────┘
           │            │
     ┌─────▼────┐ ┌─────▼────┐
     │  Local   │ │  Cloud   │
     │  Testing │ │  Servers │
     └──────────┘ └──────────┘

Cloud Infrastructure:
├── Load Balancer
├── Web Servers (Auto-scaling)
├── AI/ML Inference Servers (GPU)
├── Database Servers (Master-Slave)
├── Cache Servers (Redis Cluster)
├── Object Storage (S3-compatible)
├── Message Queue (RabbitMQ/Kafka)
└── Monitoring Stack (Prometheus, Grafana)
```

---

## 📝 **TÓM TẮT CÁC WORKFLOW CHÍNH**

1. **Admin Crawl Workflow**: Nhập link Shopee → Crawl dữ liệu → Xử lý ảnh → Phân loại → Lưu database
2. **AI Training Workflow**: Chuẩn bị dữ liệu → Training model → Đánh giá → Triển khai → Continuous learning
3. **User Try-On Workflow**: Upload ảnh → AI phân tích body → Gợi ý outfit → Virtual try-on → Mua hàng
4. **System Integration**: Frontend ↔ Backend ↔ AI Services ↔ Database

**Thời gian ước tính:**
- Crawl system: 2-3 tuần
- AI training pipeline: 4-6 tuần
- User interface: 3-4 tuần
- Integration & testing: 2-3 tuần
- Tổng: ~3-4 tháng cho MVP

**Team cần thiết:**
- Backend Developer (Python)
- Frontend Developer (React/Vue)
- AI/ML Engineer
- Data Engineer (cho crawl system)
- UI/UX Designer

**Công nghệ chính:**
- Backend: Python (Flask/FastAPI)
- Frontend: React/Vue.js
- AI: PyTorch/TensorFlow, OpenCV
- Database: PostgreSQL, Redis
- Deployment: Docker, Kubernetes
- Cloud: AWS/GCP/Azure

---

**LƯU Ý CHO ANTIGRAVITY:**
- Bắt đầu với MVP đơn giản trước
- Ưu tiên crawl 1-2 shop để có dữ liệu training
- Dùng rule-based trước khi train AI phức tạp
- Tập trung vào user experience cho try-on
- Implement tracking ngay từ đầu để collect data
- Chia nhỏ tasks và test từng component

Hệ thống này có thể scale từ nhỏ đến lớn tùy theo nhu cầu và tài nguyên. Bắt đầu với core features rồi mở rộng dần! 🚀
