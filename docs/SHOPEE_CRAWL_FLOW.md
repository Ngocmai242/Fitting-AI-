# 🏆 FLOW CRAWL SHOPEE CHUẨN 2026 (Không phụ thuộc API)

## 🎯 Mục tiêu

- Crawl đúng sản phẩm shop
- Không lỗi shopid
- Không phụ thuộc reverse API
- Dùng lâu dài

---

## 🧠 Tư duy đúng (QUAN TRỌNG)

Shopee hiện là **Frontend-driven platform**.

Nghĩa là: data thật chỉ xuất hiện khi:

- Render JS
- Scroll trang
- Load network API

**=> Crawl phải giống người dùng thật.**

---

## 🏗️ KIẾN TRÚC CHUẨN

```
Browser crawler (Playwright)
        ↓
Intercept network JSON
        ↓
Chuẩn hóa dữ liệu
        ↓
AI feature extraction
        ↓
SQLite / DB
```

---

## 🚀 FLOW CHI TIẾT

### 🥇 Bước 1 — Mở shop bằng browser thật

**Làm gì:**

- Dùng Chromium automation (Playwright)
- Không dùng requests API trực tiếp
- Không fake Googlebot

**Mục tiêu:** Render trang như user thật.

---

### 🥈 Bước 2 — Đợi trang load hoàn chỉnh

Shopee load theo tầng:

1. HTML skeleton  
2. JS bundle  
3. API lazy load  

**=> Phải wait đủ lâu** (ví dụ 3–5 giây sau `domcontentloaded`).

---

### 🥉 Bước 3 — Scroll để load full sản phẩm (hoặc gọi search_items có session)

Shopee dùng **Infinite scroll pagination**:

- Không có `page=2` kiểu truyền thống
- Scroll → gọi API `search_items` → render thêm sản phẩm

**Flow:**

```
Scroll (hoặc gọi search_items với offset)
   ↓
API search_items gọi
   ↓
Render thêm / thu thập itemid
```

Lặp lại đến khi:

- Không load thêm sản phẩm, hoặc  
- Đạt limit đặt trước

---

### 🧠 Bước 4 — Intercept network JSON (QUAN TRỌNG NHẤT)

Thay vì:

- ❌ Parse HTML  
- ❌ Reverse API (gọi API từ script không có session)

**=> Bắt trực tiếp JSON từ network** (hoặc dùng browser `fetch()` với session đã có từ navigation).

**Cụ thể:** Bắt response chứa:

- `search_items`
- `item/get`
- `get_shop_base_v2` (để lấy **shopid thật**)

Đây là data Shopee thật, không lỗi shopid nếu lấy từ API sau khi đã vào trang shop.

---

### 🧾 Bước 5 — Chuẩn hóa dữ liệu

Từ JSON lấy:

- `itemid`, `shopid`
- `name`, `image`, `price` (min/max)
- `category` (hoặc categories)

Chuẩn hóa thành **schema thống nhất** (tên trường, đơn vị giá, URL ảnh gốc).

---

### 🧠 Bước 6 — AI Feature Extraction

Dùng pipeline có sẵn:

```
name + shopee category
        ↓
FeatureExtractor
```

Extract:

- `item_type`
- fashion category
- `style`, `color`, `season`

**=> Phục vụ AI phối đồ.**

---

### 💾 Bước 7 — Lưu database

Schema gợi ý:

**Bảng products**

- id, name, shop, price, url, image  
- (shopid, itemid để sync với Shopee)

**Bảng AI features** (hoặc cột trong products)

- category_ai, item_type, color, style, season

---

## 🛡️ Bước 8 — Anti-detect (Production)

Để crawl ổn định lâu dài:

- Random delay khi scroll / giữa request
- Headless stealth (playwright-stealth hoặc tương đương)
- Cookie reuse (cùng context cho cả navigation + fetch)
- Retry nếu fail (exponential backoff)

---

## ⚡ Flow Production hoàn chỉnh

```
Input shop URL
      ↓
Browser open shop
      ↓
Wait JS load
      ↓
Auto scroll / Paginate search_items
      ↓
Intercept JSON API (get_shop_base_v2, search_items, item/get)
      ↓
Deduplicate products (itemid)
      ↓
AI feature extraction
      ↓
Save SQLite / DB
```

---

## 🧠 Vì sao flow này ổn định nhất

| Tiêu chí           | API crawl (reverse) | Browser crawl |
|--------------------|---------------------|----------------|
| Bị 403             | Dễ                 | Rất thấp       |
| Sai shopid         | Có                 | Không         |
| Full sản phẩm       | Không chắc         | Gần 100%       |
| Maintain lâu dài    | Khó                | Dễ             |

---

## 🎯 Khi nào dùng hybrid

Nếu sau này scale lớn:

```
Try API (nhanh, có session)
     ↓ fail
Browser fallback (scroll + intercept)
```

**=> 99% uptime.**

---

## 💡 Tối ưu cho project AI phối đồ

Vì không cần realtime và không cần hàng triệu shop:

**=> Browser crawler (Playwright) + intercept / fetch-in-browser là đủ tốt.**

---

## 🏁 Tóm tắt

### ĐỪNG

- Reverse API từ bên ngoài (không session)
- Fake Googlebot
- Parse HTML để lấy list sản phẩm / shopid

### NÊN

- Browser automation (Playwright)
- Intercept network JSON hoặc fetch trong browser (cùng session)
- Kết hợp AI extractor (category, style, color, season)
- Lưu schema chuẩn cho AI outfit

---

## 📎 Tham chiếu trong codebase

- **Crawler thực tế:** `data_engine/crawler/shopee.py` (v81)  
  - Navigate → intercept `get_shop_base_v2` → `search_items` (browser fetch) → `item/get` → `_build()` + FeatureExtractor → return list products.
- **Workflow tổng:** `docs/PROJECT_WORKFLOW.md` (Workflow 1: Crawl Shopee).

Nếu cần mở rộng: *"viết flow scale lớn hơn"* (10k shop, schema DB chuẩn, pipeline crawl + training AI).
