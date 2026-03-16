import requests
import sqlite3
import json
import re
import time
import random
import os

# ─── SESSION GIẢ LẬP ĐỂ GIỮ COOKIE ──────────────────────────────────────────
session = requests.Session()

# Tập hợp các User-Agent để xoay vòng nếu bị block
UA_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
]

def get_headers(referer="https://shopee.vn/"):
    return {
        'User-Agent': random.choice(UA_LIST),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': referer,
        'X-API-SOURCE': 'pc',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Shopee-Language': 'vi',
    }

def init_session():
    """Khởi tạo session chính thức"""
    try:
        session.get("https://shopee.vn/", headers={'User-Agent': UA_LIST[0]}, timeout=10)
    except:
        pass

# ─── TRÍCH XUẤT ID SHOP ─────────────────────────────────────────────────────
def extract_shop_id(shop_url: str) -> str | None:
    """Xác định Shop ID từ URL hoặc Username"""
    if not shop_url: return None
    
    # 1. Nếu có ID trực tiếp trong URL (format: .123456)
    match = re.search(r'\.(\d{6,15})(\?|$)', shop_url)
    if match: return match.group(1)
    
    # 2. Link mobile dạng /shop/123456
    match = re.search(r'/shop/(\d+)', shop_url)
    if match: return match.group(1)

    # 3. Lấy Username để resolve qua API
    clean_url = shop_url.split('?')[0].rstrip('/')
    username = clean_url.split('/')[-1]
    
    if username and username not in ['shopee.vn', '']:
        url = f'https://shopee.vn/api/v4/shop/get_shop_detail?username={username}'
        try:
            r = session.get(url, headers=get_headers(), timeout=10)
            data = r.json()
            sid = data.get('data', {}).get('shopid')
            if sid: return str(sid)
        except: pass

    # 4. Fallback cuối cùng: Quét HTML
    try:
        r = session.get(shop_url, headers=get_headers(), timeout=10)
        match = re.search(r'"shopid":\s*(\d+)', r.text)
        if match: return match.group(1)
    except: pass
    
    return None

def get_shop_info(shop_id: str) -> dict:
    """Lấy profile shop"""
    url = f'https://shopee.vn/api/v4/shop/get_shop_detail?shopid={shop_id}'
    try:
        r = session.get(url, headers=get_headers(), timeout=10)
        data = r.json()
        d = data.get('data', {})
        return {
            'name': d.get('name', 'Shopee Store'),
            'username': d.get('account', {}).get('username', ''),
            'id': shop_id
        }
    except:
        return {'name': 'Shopee Store', 'id': shop_id}

# ─── FETCH SẢN PHẨM ────────────────────────────────────────────────────────
def fetch_product_page(shop_id: str, offset: int = 0, limit: int = 50, referer: str = "https://shopee.vn/") -> list:
    """Thử nhiều API để lấy danh sách sản phẩm"""
    
    apis = [
        # Format 1: Recommend API (Thường hoạt động tốt cho Mobile/Home)
        f'https://shopee.vn/api/v4/recommend/recommend?bundle=shop_page_product_tab_main&limit={limit}&newest={offset}&shopid={shop_id}&sort_type=1',
        # Format 2: Official Search API
        f'https://shopee.vn/api/v4/shop/search_items?shopid={shop_id}&limit={limit}&offset={offset}',
    ]
    
    for url in apis:
        try:
            r = session.get(url, headers=get_headers(referer), timeout=15)
            if r.status_code == 200:
                data = r.json()
                
                # Parse format Recommend
                if 'sections' in str(data):
                    sections = data.get('data', {}).get('sections', [])
                    for s in sections:
                        items = s.get('data', {}).get('item', [])
                        if items: return items
                
                # Parse format Search
                items = data.get('items') or data.get('data', {}).get('items')
                if items: return items
                
            elif r.status_code == 403:
                # Nếu bị 403, có thể do thiếu cookie hoặc IP bị check gắt
                print(f"[Crawler] Bi chan (403) tai API: {url}")
        except:
            continue
    return []

def crawl_shop(shop_url: str, target_count: int = 40) -> dict:
    """Hàm chính để crawl toàn bộ shop"""
    init_session()
    
    shop_id = extract_shop_id(shop_url)
    if not shop_id:
        return {'success': False, 'error': 'Khong trich xuat duoc Shop ID. Hay thu link khac.', 'products': []}

    info = get_shop_info(shop_id)
    shop_name = info['name']
    shop_profile_url = f"https://shopee.vn/{info['username']}" if info['username'] else shop_url

    all_raw = []
    limit_per_page = 30
    
    # Crawl tuần tự (Slow and Steady)
    for offset in range(0, target_count, limit_per_page):
        print(f"[Crawler] Dang lay san pham tu offset {offset}...")
        page_items = fetch_product_page(shop_id, offset, limit_per_page, shop_profile_url)
        if not page_items:
            break
            
        all_raw.extend(page_items)
        if len(all_raw) >= target_count: break
        time.sleep(random.uniform(2, 4)) # Delay kỹ hơn để tránh block

    if not all_raw:
        return {
            'success': False, 
            'error': 'Shopee dang chan robot cua ban (Loi 403). Hay thu lai sau 5-10 phut hoac thu link shop khac.',
            'products': [],
            'shop_name': shop_name
        }

    # Normalize & Deduplicate
    products = []
    for item in all_raw:
        if not item: continue
        products.append(normalize_product(item, shop_id, shop_name))
        
    unique_products = deduplicate_products(products)[:target_count]

    return {
        'success': True,
        'shop_id': shop_id,
        'shop_name': shop_name,
        'shop_url': shop_profile_url,
        'total_crawled': len(unique_products),
        'products': unique_products
    }

def normalize_product(item: dict, shop_id: str, shop_name: str) -> dict:
    """Chuẩn hóa dữ liệu sản phẩm"""
    basic = item.get('item_basic') or item
    
    item_id = str(basic.get('itemid', ''))
    name = basic.get('name', 'San pham Shopee')
    
    # Image
    img_id = basic.get('image') or (basic.get('images') or [''])[0]
    img_url = f"https://cf.shopee.vn/file/{img_id}" if img_id else ""
    
    # Price
    price_val = (basic.get('price') or basic.get('price_min', 0)) / 100000
    price_display = f"{price_val:,.0f} VND".replace(',', '.')
    
    # URL
    name_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    url = f"https://shopee.vn/{name_slug}-i.{shop_id}.{item_id}"
    
    return {
        'id': f"{shop_id}_{item_id}",
        'name': name,
        'price': price_val,
        'price_display': price_display,
        'image': img_url,
        'link': url,
        'product_url': url,
        'shopee_link': url,
        'shop_id': str(shop_id),
        'shop_name': shop_name,
        'item_id': item_id,
        'rating': basic.get('item_rating', {}).get('rating_star', 0),
        'sold_count': basic.get('historical_sold', 0),
        'shopee_cat_id': basic.get('catid')
    }

def deduplicate_products(products: list) -> list:
    """Loại bỏ sản phẩm trùng tên (các variant)"""
    seen = set()
    res = []
    for p in products:
        # Lấy 30 ký tự đầu để so sánh tên gốc
        base = p['name'][:30].lower().strip()
        if base not in seen:
            seen.add(base)
            res.append(p)
    return res

def save_products_to_db(products: list, db_path: str = 'database/database_v2.db'):
    """Lưu vào database"""
    if not products: return 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Đảm bảo bảng tồn tại
        cursor.execute("CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, name TEXT, price REAL, price_display TEXT, image TEXT, link TEXT, shop_id TEXT, shop_name TEXT, item_id TEXT, color TEXT, category TEXT, style TEXT)")
        
        saved = 0
        for p in products:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO products (id, name, price, price_display, image, link, shop_id, shop_name, item_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (p['id'], p['name'], p['price'], p['price_display'], p['image'], p['link'], p['shop_id'], p['shop_name'], p['item_id']))
                saved += 1
            except: continue
            
        conn.commit()
        conn.close()
        return saved
    except Exception as e:
        print(f"DB Error: {e}")
        return 0
