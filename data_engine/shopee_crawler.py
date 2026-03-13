import requests
import sqlite3
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import os

# ─── HEADERS GIẢ LẬP MOBILE APP ────────────────────────────────────────────
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
    'Referer': 'https://shopee.vn/',
    'Accept': 'application/json',
    'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5',
    'X-API-SOURCE': 'pc',
    'X-Shopee-Language': 'vi',
}

# ─── EXTRACT SHOP ID TỪ URL ─────────────────────────────────────────────────
def extract_shop_id(shop_url: str) -> str | None:
    """
    Hỗ trợ các format URL Shopee:
    - https://shopee.vn/shop-name.123456789
    - https://shopee.vn/username
    - https://shopee.vn/shop/123456789
    """
    # Format: .{shopId} ở cuối URL
    match = re.search(r'\.(\d{6,12})\/?$', shop_url)
    if match:
        return match.group(1)

    # Format: /shop/(\d+)
    match = re.search(r'/shop/(\d+)', shop_url)
    if match:
        return match.group(1)

    # Format: username → resolve qua API
    username = shop_url.rstrip('/').split('/')[-1]
    return resolve_shop_id_by_username(username)


def resolve_shop_id_by_username(username: str) -> str | None:
    """Resolve username → shopId qua Shopee API"""
    try:
        url = f'https://shopee.vn/api/v4/shop/get_shop_detail?username={username}'
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        return str(data.get('data', {}).get('shopid', ''))
    except Exception:
        return None


# ─── FETCH 1 PAGE SẢN PHẨM (50 items) ──────────────────────────────────────
def fetch_product_page(shop_id: str, offset: int = 0, limit: int = 50) -> list:
    """Fetch 1 page = 50 sản phẩm từ Shopee API"""
    url = (
        f'https://shopee.vn/api/v4/recommend/recommend'
        f'?bundle=shop_page_product_tab_main'
        f'&limit={limit}&newest={offset}&shopid={shop_id}&sort_type=1'
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            # Rate limit → đợi rồi retry
            time.sleep(2 + random.random() * 2)
            r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        return data.get('data', {}).get('sections', [{}])[0].get('data', {}).get('item', [])
    except Exception as e:
        print(f'[Crawler] Lỗi fetch page offset={offset}: {e}')
        return []


# ─── CRAWL 40+ SẢN PHẨM SONG SONG ──────────────────────────────────────────
def crawl_shop(shop_url: str, target_count: int = 40) -> dict:
    """
    Crawl shop Shopee, trả về list sản phẩm đã normalize.
    target_count: số sản phẩm cần lấy (default 40, max 100/lần)
    """
    shop_id = extract_shop_id(shop_url)
    if not shop_id:
        return {'success': False, 'error': 'Không tìm được Shop ID', 'products': []}

    # Tính số page cần fetch (mỗi page = 50 items)
    pages_needed = max(1, -(-target_count // 50))  # ceiling division
    offsets = [i * 50 for i in range(pages_needed)]

    # Fetch SONG SONG tất cả pages
    all_raw = []
    with ThreadPoolExecutor(max_workers=min(pages_needed, 4)) as executor:
        futures = {
            executor.submit(fetch_product_page, shop_id, offset): offset
            for offset in offsets
        }
        for future in as_completed(futures):
            items = future.result()
            all_raw.extend(items)

    # Normalize & deduplicate
    products = [normalize_product(item, shop_id) for item in all_raw if item]
    unique_products = deduplicate_products(products)[:target_count]

    return {
        'success': True,
        'shop_id': shop_id,
        'total_crawled': len(unique_products),
        'products': unique_products,
    }


# ─── NORMALIZE: 1 sản phẩm, 1 màu, 1 ảnh ───────────────────────────────────
def normalize_product(item: dict, shop_id: str) -> dict:
    """Chuẩn hóa raw item → product schema"""
    # Lấy ảnh đầu tiên (màu mặc định)
    raw_image = item.get('image') or (item.get('images') or [''])[0]
    image_url = f'https://cf.shopee.vn/file/{raw_image}_tn' if raw_image else None

    # Giá (Shopee: đơn vị = VND * 100000)
    price_raw = item.get('price_min') or item.get('price', 0)
    price_max_raw = item.get('price_max', price_raw)
    price = price_raw / 100000
    price_max = price_max_raw / 100000

    if price == price_max:
        price_display = f"{price:,.0f}đ".replace(',', '.')
    else:
        price_display = f"{price:,.0f} - {price_max:,.0f}đ".replace(',', '.')

    # Link mở Shopee trực tiếp
    item_id = item.get('itemid', '')
    name_slug = re.sub(r'\s+', '-', item.get('name', ''))
    product_link = f'https://shopee.vn/{name_slug}-i.{shop_id}.{item_id}'

    return {
        'id': f"{shop_id}_{item_id}",
        'name': item.get('name', ''),
        'price': round(price, 0),
        'price_display': price_display,
        'image': image_url,          # CHỈ 1 ảnh đại diện
        'link': product_link,        # Link mở Shopee
        'shopee_cat_id': item.get('catid'),
        'shop_id': shop_id,
        'item_id': str(item_id),
        'rating': item.get('item_rating', {}).get('rating_star', 0),
        'sold_count': item.get('historical_sold', 0),
    }


# ─── DEDUPLICATE: Loại sản phẩm trùng (khác màu cùng tên) ──────────────────
def deduplicate_products(products: list) -> list:
    """Giữ 1 sản phẩm / tên gốc (bỏ variant màu sắc)"""
    seen = set()
    result = []
    color_words = r'\s*[-–]\s*(đen|trắng|đỏ|xanh|vàng|hồng|tím|xám|nâu|kem|cam|be|nude|navy|caramel|be|trơn).*$'

    for p in products:
        base_name = re.sub(color_words, '', p['name'], flags=re.IGNORECASE).strip().lower()
        if base_name not in seen:
            seen.add(base_name)
            result.append(p)
    return result


# ─── LƯU VÀO SQLITE ─────────────────────────────────────────────────────────
def save_products_to_db(products: list, db_path: str = None):
    """Lưu sản phẩm đã crawl vào SQLite"""
    if db_path is None:
        # Default path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(base_dir, '..', 'database', 'database_v2.db'))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tạo bảng nếu chưa có
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL,
            price_display TEXT,
            image TEXT,
            link TEXT,
            shopee_cat_id INTEGER,
            shop_id TEXT,
            item_id TEXT,
            rating REAL,
            sold_count INTEGER,
            category TEXT,
            classification TEXT,  -- JSON string
            crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            image_url TEXT,
            color TEXT,
            is_primary INTEGER DEFAULT 1,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    saved = 0
    for p in products:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO products
                (id, name, price, price_display, image, link,
                 shopee_cat_id, shop_id, item_id, rating, sold_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p['id'], p['name'], p['price'], p['price_display'],
                p['image'], p['link'], p['shopee_cat_id'],
                p['shop_id'], p['item_id'], p['rating'], p['sold_count']
            ))

            # Lưu ảnh vào product_images
            if p['image']:
                cursor.execute('''
                    INSERT OR IGNORE INTO product_images (product_id, image_url, is_primary)
                    VALUES (?, ?, 1)
                ''', (p['id'], p['image']))

            saved += 1
        except Exception as e:
            print(f'[DB] Lỗi lưu sản phẩm {p["id"]}: {e}')

    conn.commit()
    conn.close()
    return saved
