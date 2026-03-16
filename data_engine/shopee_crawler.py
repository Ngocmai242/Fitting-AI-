"""
data_engine/shopee_crawler.py
Shopee Crawler – Playwright + Stealth + XHR Intercept (2025)

Đầu ra mỗi sản phẩm:
  name          tên sản phẩm
  price         giá VND (số nguyên, ví dụ 150000)
  price_display giá hiển thị (ví dụ "150.000đ" hoặc "100.000 - 200.000đ")
  image_url     URL ảnh đầy đủ (https://down-vn.img.susercontent.com/file/...)
  category      tên danh mục tiếng Việt (ví dụ "Áo")
  category_id   id danh mục số
  product_url   link sản phẩm đầy đủ trên shopee.vn
  shop_id       id shop
  item_id       id sản phẩm
  rating        điểm đánh giá (0–5)
  sold_count    số đã bán

Yêu cầu: chạy shopee_login.py trước để có shopee_cookies.json
"""

import asyncio, json, os, re, sqlite3, random
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def stealth(page):
    """Helper to apply stealth using the current playwright-stealth API"""
    await Stealth().apply_stealth_async(page)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, 'shopee_cookies.json')

# ─── MAP category_id → tên tiếng Việt ───────────────────────────────────────
CATEGORY_MAP = {
    100001: 'Thiết Bị Điện Tử',
    100006: 'Điện Thoại & Phụ Kiện',
    100009: 'Máy Tính & Laptop',
    100010: 'Máy Ảnh & Máy Quay Phim',
    100011: 'Thời Trang Nam',
    100012: 'Thời Trang Nữ',
    100013: 'Đồng Hồ',
    100014: 'Giày Dép Nam',
    100015: 'Giày Dép Nữ',
    100016: 'Túi Ví Nữ',
    100017: 'Phụ Kiện & Trang Sức Nữ',
    100018: 'Sức Khỏe',
    100019: 'Sắc Đẹp',
    100020: 'Nhà Cửa & Đời Sống',
    100021: 'Bếp',
    100022: 'Đồ Chơi & Mẹ Bé',
    100023: 'Sách & Tạp Chí',
    100024: 'Thể Thao & Du Lịch',
    100025: 'Ô Tô & Xe Máy & Xe Đạp',
    100026: 'Bách Hóa Online',
    100027: 'Thú Cưng',
    100033: 'Voucher & Dịch Vụ',
    100034: 'Thực Phẩm & Đồ Uống',
    100035: 'Thiết Bị Điện Gia Dụng',
    100036: 'Điện Gia Dụng',
    100037: 'Thời Trang Trẻ Em',
    100039: 'Balo & Túi Ví Nam',
    100040: 'Túi Ví & Balo Nữ',
    100042: 'Chăm Sóc Nhà Cửa',
    100044: 'Nội Thất & Decor',
    100050: 'Thể Thao',
    100634: 'Thời Trang',
    100633: 'Thời Trang',
}


async def _make_context(playwright):
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
        ]
    )
    ctx = await browser.new_context(
        viewport={'width': 1280, 'height': 800},
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        locale='vi-VN',
        timezone_id='Asia/Ho_Chi_Minh',
        extra_http_headers={
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5',
            'Referer': 'https://shopee.vn/',
        },
    )
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, encoding='utf-8') as f:
            cookies = json.load(f)
        await ctx.add_cookies(cookies)
        print(f'[Crawler] Loaded {len(cookies)} cookies')
    else:
        print(f'[Crawler] WARNING: {COOKIES_FILE} not found')
        print('[Crawler] Run shopee_login.py first!')
    return browser, ctx


async def _resolve_shop_id(page, shop_url: str) -> str | None:
    clean = shop_url.split('?')[0].rstrip('/')

    m = re.search(r'\.(\d{6,12})$', clean)
    if m:
        return m.group(1)

    m = re.search(r'/shop/(\d+)', clean)
    if m:
        return m.group(1)

    username = [p for p in urlparse(clean).path.split('/') if p]
    if not username:
        return None
    username = username[-1]
    print(f'[Crawler] Resolving username: {username}')

    found_id = None

    async def _catch(response):
        nonlocal found_id
        if found_id:
            return
        if 'get_shop_detail' in response.url or 'shop_page' in response.url:
            try:
                d = await response.json()
                sid = (
                    d.get('data', {}).get('shopid')
                    or d.get('data', {}).get('basic', {}).get('shopid')
                )
                if sid:
                    found_id = str(sid)
            except Exception:
                pass

    page.on('response', _catch)
    await stealth(page)
    await page.goto(clean, wait_until='networkidle', timeout=30000)
    await page.wait_for_timeout(2000)

    if not found_id:
        body = await page.content()
        m = re.search(r'"shopid"\s*:\s*(\d+)', body)
        if m:
            found_id = m.group(1)

    return found_id


_category_cache: dict[int, str] = {}


async def _get_category_name(ctx, cat_id: int) -> str:
    if not cat_id:
        return 'Khác'

    if cat_id in CATEGORY_MAP:
        return CATEGORY_MAP[cat_id]

    if cat_id in _category_cache:
        return _category_cache[cat_id]

    try:
        page = await ctx.new_page()
        await stealth(page)
        url = f'https://shopee.vn/api/v4/search/get_fe_category_detail?catids={cat_id}'
        result = None

        async def _grab(response):
            nonlocal result
            if 'get_fe_category_detail' in response.url:
                try:
                    result = await response.json()
                except Exception:
                    pass

        page.on('response', _grab)
        await page.goto(url, wait_until='commit', timeout=10000)
        await page.wait_for_timeout(1500)
        await page.close()

        if result:
            cats = result.get('data', {}).get('category_list', [])
            if not cats:
                cats = result.get('data', {}).get('categories', [])
            for c in cats:
                if str(c.get('catid', '')) == str(cat_id):
                    name = c.get('display_name') or c.get('name', f'Cat-{cat_id}')
                    _category_cache[cat_id] = name
                    return name
    except Exception as e:
        print(f'[Crawler] Category API error for {cat_id}: {e}')

    fallback = f'Danh mục {cat_id}'
    _category_cache[cat_id] = fallback
    return fallback


def _build_image_url(image_key: str) -> str | None:
    if not image_key:
        return None
    if image_key.startswith('http'):
        return image_key
    return f'https://down-vn.img.susercontent.com/file/{image_key}'
    

async def _fetch_clean_image(ctx, shop_id, item_id) -> str | None:
    """
    Truy cập trang chi tiết sản phẩm, lấy mảng ảnh sạch (gallery) và chọn ảnh đại diện tốt nhất.
    """
    page = await ctx.new_page()
    images = []
    
    async def _intercept(response):
        nonlocal images
        url = response.url
        if ('pdp/get_pc' in url 
                or 'get_item_detail' in url 
                or ('pdp/' in url and 'item_id=' + str(item_id) in url and 'get_rating' not in url)):
            try:
                data = await response.json()
                it = data.get('data', {}).get('item', {}) or data.get('data', {}) or data.get('item', {}) or data
                
                # 1. Ưu tiên lấy từ tier_variations (ảnh từng màu/loại) - ĐÂY LÀ ẢNH SẠCH NHẤT (Ảnh 1)
                tier_v = it.get('tier_variations', [])
                variation_images = []
                if tier_v:
                    for v in tier_v:
                        v_imgs = v.get('images', [])
                        if v_imgs:
                            variation_images.extend([img for img in v_imgs if img and isinstance(img, str)])
                
                if variation_images:
                    # Nếu có ảnh phân loại, thường đây là các ảnh đơn sản phẩm rất sạch
                    # Chúng ta lấy toàn bộ để lát nữa chọn ở giữa
                    images = variation_images
                    # print(f'[Cleaner] Found {len(images)} variation images for {item_id}')
                    return

                # 2. Fallback: Lấy từ gallery chính (Nếu không có phân loại màu sắc)
                raw_imgs = it.get('images', [])
                if raw_imgs:
                    # Bỏ qua ít nhất 3 ảnh đầu tiên theo yêu cầu (0: video/ảnh bìa, 1-2: ảnh ghép/quảng cáo)
                    # User yêu cầu lấy từ ảnh thứ 4 hoặc 5 trở đi
                    if len(raw_imgs) >= 6:
                        images = [img for img in raw_imgs[4:] if img and isinstance(img, str)]
                    elif len(raw_imgs) >= 4:
                        images = [img for img in raw_imgs[3:] if img and isinstance(img, str)]
                    elif len(raw_imgs) > 1:
                        images = [img for img in raw_imgs[1:] if img and isinstance(img, str)]
                    else:
                        images = [img for img in raw_imgs if img and isinstance(img, str)]
            except Exception:
                pass
                
    try:
        # 1. Đăng ký listener TRƯỚC khi navigate
        page.on('response', _intercept)
        await stealth(page)
        
        # Shopee URL format
        url = f'https://shopee.vn/product/{shop_id}/{item_id}'
        print(f'[Cleaner] Fetching clean image for product: {item_id}')
        
        # 2. Dùng domcontentloaded để không bị kết thúc sớm bởi networkidle
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # 3. Chờ lâu hơn để XHR kịp về
        await page.wait_for_timeout(4000)
        
        # 4. Fallback: Nếu vẫn rỗng, scroll nhẹ để kích hoạt lazy load
        if not images:
            # print(f'[Cleaner] No images yet for {item_id}, scrolling...')
            await page.evaluate('window.scrollBy(0, 200)')
            await page.wait_for_timeout(2500)
            
        if not images:
            return None
            
        # 5. Chọn ảnh ở vị trí giữa gallery (thường là ảnh chính diện đơn sản phẩm)
        # Theo yêu cầu của user: hình có 1 sản phẩm thường ở giữa list các hình
        n = len(images)
        if n >= 3:
            # Ưu tiên lấy ảnh ở vị trí 1/2 hoặc 2/3 nếu có nhiều ảnh
            # Thông thường ảnh index 2, 3 là ảnh đơn sản phẩm tốt nhất
            idx = n // 2
            clean_key = images[idx]
        elif n == 2:
            clean_key = images[1] # Thường ảnh 2 là ảnh thật, ảnh 1 là ảnh bìa ghép
        else:
            clean_key = images[0]
            
        print(f'[Cleaner] Selected image index {n // 2} of {n} for {item_id}')
            
        return _build_image_url(clean_key)
    except Exception as e:
        print(f'[Cleaner] Error fetching {item_id}: {e}')
        return None
    finally:
        await page.close()


def _normalize(item: dict, shop_id: str, category_name: str) -> dict | None:
    item_id = item.get('itemid') or item.get('item_id')
    if not item_id:
        return None

    # Thử lấy ảnh từ nhiều nguồn theo thứ tự ưu tiên
    raw_img = (
        item.get('image')
        or (item.get('images') or [''])[0]
        or item.get('image_url', '')
    )
    image_url = _build_image_url(raw_img) if raw_img else None

    price_raw     = item.get('price_min') or item.get('price', 0)
    price_max_raw = item.get('price_max', price_raw)
    price     = int(price_raw / 100000)
    price_max = int(price_max_raw / 100000)

    if price == price_max or price_max == 0:
        price_display = f"{price:,}đ".replace(',', '.')
    else:
        price_display = f"{price:,} - {price_max:,}đ".replace(',', '.')

    name = (item.get('name') or '').strip() or 'Sản phẩm'
    name_slug = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '-')
    product_url = f'https://shopee.vn/{name_slug}-i.{shop_id}.{item_id}'

    return {
        'id':            f'{shop_id}_{item_id}',
        'name':          name,
        'price':         price,
        'price_display': price_display,
        'image_url':     image_url,
        'category':      category_name,
        'category_id':   item.get('catid'),
        'product_url':   product_url,
        'shop_id':       str(shop_id),
        'item_id':       str(item_id),
        'rating':        item.get('item_rating', {}).get('rating_star', 0),
        'sold_count':    item.get('historical_sold', 0),
    }


async def _fetch_products(ctx, shop_id: str, target_count: int) -> list:
    raw_items: list[dict] = []
    page = await ctx.new_page()

    async def _handle(response):
        url = response.url
        # Bắt thêm các endpoint chứa danh sách sản phẩm chính của shop
        if ('recommend/recommend' in url or
            'rcmd_items' in url or
            'get_items_with_bundle' in url or
            'api/v4/shop/search_items' in url or
            'api/v4/search/search_items' in url or
            'api/v4/shop/get_shop_base' in url): # Bắt thêm base API để đảm bảo không bỏ lỡ dữ liệu
            try:
                data = await response.json()
                items_found = []
                
                # Cấu trúc của shop search items
                if 'search_items' in url:
                    items_found = data.get('items') or data.get('data', {}).get('items', [])
                elif 'get_shop_base' in url:
                    # Đôi khi shop base trả về một ít sản phẩm nổi bật
                    items_found = data.get('data', {}).get('top_products', [])
                else:
                    # Cấu trúc của recommend
                    for sec in data.get('data', {}).get('sections', []):
                        items_found.extend(sec.get('data', {}).get('item', []))
                    items_found.extend(data.get('data', {}).get('items', []))
                    if not items_found: # Thử thêm path khác cho recommend
                        items_found = data.get('item_list', []) or data.get('items', [])
                
                if items_found:
                    # Lọc trùng ngay khi intercept để đếm chính xác
                    new_count = 0
                    for item in items_found:
                        iid = str(item.get('itemid') or item.get('item_id'))
                        if iid and not any(str(x.get('itemid') or x.get('item_id')) == iid for x in raw_items):
                            raw_items.append(item)
                            new_count += 1
                    
                    if new_count > 0:
                        print(f'[Crawler] Intercepted {new_count} NEW items → total unique: {len(raw_items)}')
            except Exception:
                pass

    page.on('response', _handle)
    await stealth(page)

    shop_page_url = f'https://shopee.vn/shop/{shop_id}'
    # Đảm bảo vào tab "Tất cả sản phẩm" và sắp xếp theo mới nhất để tránh cache
    target_url = f'{shop_page_url}/search?page=0&sortBy=ctime' 
    print(f'[Crawler] Opening: {target_url}')
    await page.goto(target_url, wait_until='domcontentloaded', timeout=40000)
    await page.wait_for_timeout(4000) # Chờ lâu hơn một chút để XHR đầu tiên về

    # Tăng số lần cuộn và cuộn xa hơn để Shopee load thêm XHR
    # Với 40 sản phẩm, chúng ta cần cuộn nhiều hơn 8 lần
    max_scrolls = max(15, (target_count // 5)) 
    for i in range(max_scrolls):
        if len(raw_items) >= target_count:
            print(f'[Crawler] Reached target count ({len(raw_items)}/{target_count})')
            break
            
        # Cuộn từng đoạn 1200px thay vì 800px để trigger nhiều XHR hơn
        await page.evaluate('window.scrollBy(0, 1200)')
        await page.wait_for_timeout(1500 + random.randint(0, 1000))
        
        # Thỉnh thoảng cuộn ngược lên một chút để Shopee tưởng là người dùng thật
        if i % 3 == 0:
            await page.evaluate('window.scrollBy(0, -300)')
            await page.wait_for_timeout(800)
            
        print(f'[Crawler] Scroll {i+1}/{max_scrolls} — unique items so far: {len(raw_items)}')

    # Nếu sau khi cuộn vẫn ít, thử chuyển sang page tiếp theo (nếu có thể bằng URL)
    if len(raw_items) < target_count:
        print('[Crawler] Still below target, trying to jump to next page...')
        next_page_url = f'{shop_page_url}/search?page=1&sortBy=ctime'
        await page.goto(next_page_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)
        # Cuộn tiếp ở page mới
        for i in range(5):
            if len(raw_items) >= target_count: break
            await page.evaluate('window.scrollBy(0, 1200)')
            await page.wait_for_timeout(1500)

    if not raw_items:
        print('[Crawler] Intercept empty → trying DOM fallback')
        raw_items = await _dom_fallback(page)

    await page.close()
    return raw_items


async def _dom_fallback(page) -> list:
    items = []
    try:
        # Chờ một trong các selector phổ biến của Shopee card
        selectors = ['[data-sqe="item"]', '.shopee-search-item-result__item', '.shop-search-result-view__item']
        found_selector = None
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=4000)
                found_selector = sel
                break
            except: continue
            
        if not found_selector:
            print('[Crawler] No DOM card selector found')
            return []

        cards = await page.query_selector_all(found_selector)
        for card in cards:
            try:
                name_el  = await card.query_selector('[data-sqe="name"]')
                price_el = await card.query_selector('[class*="price"]')
                link_el  = await card.query_selector('a')
                img_el   = await card.query_selector('img')

                name       = (await name_el.inner_text()).strip()  if name_el  else ''
                price_text = (await price_el.inner_text()).strip() if price_el else '0'
                href       = await link_el.get_attribute('href')   if link_el  else ''
                img_src    = await img_el.get_attribute('src')     if img_el   else ''

                m = re.search(r'i\.\d+\.(\d+)', href or '')
                if not m:
                    continue
                item_id = m.group(1)

                digits    = re.sub(r'[^\d]', '', price_text.split('–')[0].split('-')[0])
                price_raw = int(digits) * 100000 if digits else 0

                img_key = ''
                if img_src:
                    img_key = img_src.split('/file/')[-1].split('_')[0] if '/file/' in img_src else img_src

                items.append({
                    'itemid':          item_id,
                    'name':            name,
                    'price':           price_raw,
                    'price_min':       price_raw,
                    'price_max':       price_raw,
                    'image':           img_key,
                    'catid':           None,
                    'item_rating':     {'rating_star': 0},
                    'historical_sold': 0,
                })
            except Exception:
                continue
    except Exception as e:
        print(f'[Crawler] DOM fallback error: {e}')
    print(f'[Crawler] DOM fallback: {len(items)} items')
    return items


def _dedup(products: list) -> list:
    """
    Deduplicate based on product ID (shop_id + item_id).
    """
    seen, result = set(), []
    for p in products:
        if not p:
            continue
        uid = p.get('id')
        if uid and uid not in seen:
            seen.add(uid)
            result.append(p)
    return result


def crawl_shopee_new(shop_url: str, target_count: int = 40) -> dict:
    return asyncio.run(_crawl_async(shop_url, target_count))


async def _crawl_async(shop_url: str, target_count: int) -> dict:
    print(f'[Crawler] ─── START: {shop_url}')
    async with async_playwright() as p:
        browser, ctx = await _make_context(p)
        page = await ctx.new_page()
        try:
            shop_id = await _resolve_shop_id(page, shop_url)
            await page.close()
            if not shop_id:
                return {'success': False,
                        'error': 'Không tìm được Shop ID từ URL này.',
                        'products': []}
            print(f'[Crawler] shop_id = {shop_id}')

            raw_items = await _fetch_products(ctx, shop_id, target_count)
            if not raw_items:
                return {'success': False,
                        'error': 'Không có sản phẩm. Shop có thể ở chế độ riêng tư.',
                        'products': []}

            cat_ids = list({item.get('catid') for item in raw_items if item.get('catid')})
            cat_names: dict[int, str] = {}
            for cid in cat_ids:
                cat_names[cid] = await _get_category_name(ctx, cid)

            sem = asyncio.Semaphore(3)

            async def _enrich(item):
                item_id = str(item.get('itemid') or item.get('item_id') or '')
                if item_id:
                    async with sem:
                        await asyncio.sleep(random.uniform(0.3, 1.0))
                        clean_url = await _fetch_clean_image(ctx, shop_id, item_id)
                    if clean_url:
                        item['image'] = clean_url
                    else:
                        # Fallback: lấy ảnh từ field 'images' nếu 'image' rỗng
                        if not item.get('image') and item.get('images'):
                            imgs = [x for x in item['images'] if x]
                            if imgs:
                                mid = len(imgs) // 2
                                item['image'] = imgs[mid]
                        print(f'[Cleaner] FAILED {item_id}, using thumbnail: {bool(item.get("image"))}')
                cid      = item.get('catid')
                cat_name = cat_names.get(cid, 'Khác')
                return _normalize(item, shop_id, cat_name)

            print(f'[Crawler] Enriching {len(raw_items)} products...')
            results  = await asyncio.gather(*[_enrich(i) for i in raw_items])
            products = [p for p in results if p]
            unique   = _dedup(products)[:target_count]
            print(f'[Crawler] ─── DONE: {len(unique)} sản phẩm')

            updated = await ctx.cookies()
            with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)

            return {
                'success':       True,
                'shop_id':       shop_id,
                'total_crawled': len(unique),
                'products':      unique,
            }

        except Exception as ex:
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(ex), 'products': []}
        finally:
            await browser.close()


def save_products_to_db(products: list, db_path: str = None) -> int:
    if db_path is None:
        db_path = os.path.abspath(
            os.path.join(BASE_DIR, '..', 'database', 'database_v2.db')
        )
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id         TEXT UNIQUE NOT NULL,
                name            TEXT NOT NULL,
                price           INTEGER,
                price_display   TEXT,
                image_url       TEXT,
                product_url     TEXT,
                category        TEXT,
                category_id     INTEGER,
                shop_name       TEXT,
                shop_id         TEXT,
                rating          REAL,
                sold_count      INTEGER,
                shopee_cat_id   INTEGER,
                crawl_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active       INTEGER DEFAULT 1,
                is_valid        INTEGER DEFAULT 1,
                classification  TEXT,
                ai_category     TEXT,
                clean_image_path TEXT,
                color_primary   TEXT,
                color_secondary TEXT,
                hex_primary     TEXT,
                color_tone      TEXT,
                gender          TEXT,
                fit_type        TEXT,
                season          TEXT,
                occasion        TEXT,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        existing = {row[1] for row in cur.execute('PRAGMA table_info(products)')}
        if 'category' not in existing:
            cur.execute('ALTER TABLE products ADD COLUMN category TEXT')
        if 'category_id' not in existing:
            cur.execute('ALTER TABLE products ADD COLUMN category_id INTEGER')
        
        # New columns migration
        new_cols = [
            ('clean_image_path', 'TEXT'),
            ('color_primary', 'TEXT'),
            ('color_secondary', 'TEXT'),
            ('hex_primary', 'TEXT'),
            ('color_tone', 'TEXT'),
            ('gender', 'TEXT'),
            ('fit_type', 'TEXT'),
            ('season', 'TEXT'),
            ('occasion', 'TEXT')
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing:
                try:
                    cur.execute(f'ALTER TABLE products ADD COLUMN {col_name} {col_type}')
                except Exception as e:
                    print(f"[DB] Migration error for {col_name}: {e}")
        
        conn.commit()

        if not products:
            conn.close()
            return 0

        saved = 0
        for p in products:
            try:
                cur.execute("""
                    INSERT OR REPLACE INTO products
                    (item_id, name, price, price_display, image_url, product_url,
                     category, category_id, shopee_cat_id,
                     shop_id, shop_name, rating, sold_count, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                """, (
                    p['id'],
                    p['name'],
                    p['price'],
                    p['price_display'],
                    p['image_url'],
                    p['product_url'],
                    p.get('category', ''),
                    p.get('category_id'),
                    p.get('category_id'),
                    p['shop_id'],
                    p.get('shop_name', ''),
                    p['rating'],
                    p['sold_count'],
                ))
                saved += 1
            except Exception as ex:
                print(f'[DB] Error saving {p.get("id")}: {ex}')

        conn.commit()
        conn.close()
        print(f'[DB] Saved {saved}/{len(products)} products')
        return saved
    except Exception as ex:
        print(f'[DB] Fatal: {ex}')
        return 0