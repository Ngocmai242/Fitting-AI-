import re
import sqlite3
import json
import requests
from io import BytesIO
from PIL import Image
from collections import Counter
import os

# ─── FASHION TAXONOMY ────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    'TOP': [
        'áo thun', 'áo phông', 'áo sơ mi', 'áo khoác', 'áo len',
        'áo hoodie', 'áo crop', 'áo blazer', 'áo polo', 'áo tank',
        'áo cardigan', 'áo sweater', 'áo vest', 'áo jacket', 'blouse',
        't-shirt', 'shirt', 'top ', 'áo ', 'sweater', 'hoodie'
    ],
    'BOTTOM': [
        'quần jeans', 'quần jean', 'quần tây', 'quần short', 'quần shorts',
        'quần ống rộng', 'quần legging', 'quần baggy', 'quần palazzo',
        'quần cargo', 'quần kaki', 'quần âu', 'jeans', 'quần '
    ],
    'DRESS': [
        'váy liền', 'đầm liền', 'đầm ', 'váy midi', 'váy maxi',
        'chân váy', 'váy xòe', 'váy bút chì', 'váy wrap', 'dress',
        'skirt', 'set áo váy', 'bộ váy'
    ],
    'SHOES': [
        'giày thể thao', 'giày cao gót', 'giày sandal', 'giày boots',
        'giày loafer', 'giày sneaker', 'giày bệt', 'dép', 'giày ',
        'sneaker', 'boots', 'sandal', 'heels', 'loafer', 'slipper'
    ],
    'ACCESSORY': [
        'túi xách', 'túi tote', 'ví da', 'thắt lưng', 'mũ', 'nón',
        'khăn', 'vòng tay', 'nhẫn', 'bông tai', 'dây chuyền', 'kính',
        'belt', 'bag', 'wallet', 'hat', 'scarf', 'necklace', 'earring'
    ],
    'OUTFIT': [
        'bộ đồ', 'set đồ', 'suit ', 'co-ord', 'matching set',
        'set áo quần', 'đồ bộ', 'bộ ', 'set '
    ],
}

OCCASION_KEYWORDS = {
    'WORK':     ['công sở', 'đi làm', 'văn phòng', 'business', 'formal', 'lịch sự', 'thanh lịch'],
    'PARTY':    ['tiệc', 'dự tiệc', 'sự kiện', 'party', 'event', 'clubbing', 'dạ tiệc'],
    'FESTIVAL': ['lễ hội', 'tết', 'trung thu', 'halloween', 'giáng sinh', 'festival', 'holiday'],
    'SPORT':    ['thể thao', 'gym', 'yoga', 'chạy bộ', 'sport', 'workout', 'active'],
    'BEACH':    ['đi biển', 'resort', 'beach', 'bơi', 'bikini', 'hè', 'mùa hè'],
    'DATE':     ['hẹn hò', 'date', 'romantic', 'dạo phố', 'đi chơi'],
    'DAILY':    ['hằng ngày', 'casual', 'dạo phố', 'đi chơi', 'thoải mái', 'thường ngày'],
    'FORMAL':   ['sang trọng', 'lễ nghi', 'cưới', 'tốt nghiệp', 'gala', 'luxury', 'cao cấp'],
}

STYLE_KEYWORDS = {
    'casual':      ['casual', 'thoải mái', 'đơn giản', 'basic', 'everyday'],
    'streetwear':  ['streetwear', 'street', 'hiphop', 'urban', 'oversize', 'oversized'],
    'korean':      ['ulzzang', 'kpop', 'hàn quốc', 'korean', 'oppa', 'unnie', 'y2k hàn'],
    'minimalist':  ['minimalist', 'tối giản', 'clean', 'simple', 'trơn'],
    'vintage':     ['vintage', 'retro', 'cổ điển', 'thập niên', 'boho', 'bohemian'],
    'elegant':     ['elegant', 'thanh lịch', 'sang trọng', 'tinh tế', 'feminine'],
    'sporty':      ['sporty', 'thể thao', 'active', 'athletic', 'gym'],
    'y2k':         ['y2k', 'thập niên 2000', '2000s', 'e-girl', 'aesthetic'],
}

BODY_TYPE_RECOMMENDATIONS = {
    'TOP': {
        'PEAR':              ['off-shoulder', 'rộng vai', 'cổ thuyền', 'puff sleeve'],
        'INVERTED_TRIANGLE': ['đơn giản', 'cổ chữ v', 'trơn', 'dark', 'tối màu'],
        'RECTANGLE':         ['peplum', 'crop', 'ruffles', 'họa tiết'],
        'APPLE':             ['empire', 'flowy', 'cổ v', 'dài che bụng'],
        'HOURGLASS':         ['fitted', 'wrap', 'ôm', 'nhấn eo'],
    },
    'BOTTOM': {
        'PEAR':              ['a-line', 'tối màu', 'bootcut', 'flare'],
        'INVERTED_TRIANGLE': ['wide-leg', 'palazzo', 'họa tiết', 'sáng màu'],
        'RECTANGLE':         ['high-waist', 'thắt eo', 'flare', 'ruched'],
        'APPLE':             ['bootcut', 'wide-leg', 'tối màu', 'dark'],
        'HOURGLASS':         ['high-waist', 'fitted', 'pencil'],
    },
}

# ─── COLOR MAP ───────────────────────────────────────────────────────────────
COLOR_NAMES_VI = {
    'đen': 'black', 'trắng': 'white', 'đỏ': 'red',
    'xanh dương': 'blue', 'xanh lá': 'green', 'xanh': 'blue',
    'vàng': 'yellow', 'hồng': 'pink', 'tím': 'purple',
    'cam': 'orange', 'xám': 'gray', 'nâu': 'brown',
    'kem': 'cream', 'nude': 'nude', 'navy': 'navy',
    'be': 'beige', 'caramel': 'caramel', 'trắng đen': 'black-white',
}

# RGB → color name mapping cho Pillow
RGB_COLOR_MAP = [
    ((0,   0,   0),   'black'),
    ((255, 255, 255),  'white'),
    ((200, 0,   0),   'red'),
    ((0,   0,   200), 'blue'),
    ((0,   150, 0),   'green'),
    ((255, 200, 0),   'yellow'),
    ((255, 150, 180), 'pink'),
    ((150, 0,   200), 'purple'),
    ((255, 120, 0),   'orange'),
    ((150, 150, 150), 'gray'),
    ((120, 70,  20),  'brown'),
    ((255, 240, 200), 'cream'),
    ((0,   0,   100), 'navy'),
    ((210, 180, 140), 'beige'),
]


# ─── CLASSIFY TỪ TÊN SẢN PHẨM (rule-based, instant) ─────────────────────────
def classify_by_name(product_name: str) -> dict:
    name_lower = product_name.lower()

    # Category
    category = 'UNKNOWN'
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            category = cat
            break

    # Occasions
    occasions = [
        occ for occ, keywords in OCCASION_KEYWORDS.items()
        if any(kw in name_lower for kw in keywords)
    ]
    if not occasions:
        occasions = ['DAILY']  # default

    # Styles
    styles = [
        style for style, keywords in STYLE_KEYWORDS.items()
        if any(kw in name_lower for kw in keywords)
    ]
    if not styles:
        styles = ['casual']  # default

    # Colors từ tên
    colors = [
        en_name for vi_name, en_name in COLOR_NAMES_VI.items()
        if vi_name in name_lower
    ]

    return {
        'category': category,
        'occasions': occasions,
        'styles': styles,
        'colors_from_name': colors,
    }


# ─── EXTRACT MÀU TỪ ẢNH (Pillow, hoàn toàn free) ────────────────────────────
def extract_color_from_image(image_url: str) -> str:
    """Phân tích màu chủ đạo từ ảnh sản phẩm dùng Pillow — không cần API"""
    try:
        r = requests.get(image_url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        img = Image.open(BytesIO(r.content)).convert('RGB')
        img = img.resize((50, 50))  # Resize nhỏ để xử lý nhanh

        # Lấy tất cả pixels
        pixels = list(img.getdata())

        # Loại bỏ background (gần trắng/xám nhạt)
        filtered = [
            px for px in pixels
            if not (px[0] > 220 and px[1] > 220 and px[2] > 220)  # không phải trắng
            and not (abs(px[0]-px[1]) < 20 and abs(px[1]-px[2]) < 20 and px[0] > 180)  # không phải xám nhạt
        ]

        if not filtered:
            filtered = pixels

        # Tìm màu dominant
        def color_distance(c1, c2):
            return sum((a-b)**2 for a, b in zip(c1, c2)) ** 0.5

        def nearest_color(pixel):
            return min(RGB_COLOR_MAP, key=lambda x: color_distance(pixel, x[0]))[1]

        color_counts = Counter(nearest_color(px) for px in filtered[:500])
        return color_counts.most_common(1)[0][0]

    except Exception:
        return 'unknown'


# ─── CLASSIFY ĐẦY ĐỦ 1 SẢN PHẨM ────────────────────────────────────────────
def classify_product(product: dict, analyze_image: bool = True) -> dict:
    """Phân loại đầy đủ 1 sản phẩm — 100% local, free"""
    name_result = classify_by_name(product.get('name', ''))

    # Màu từ ảnh nếu không có từ tên
    primary_color = name_result['colors_from_name'][0] if name_result['colors_from_name'] else None
    if not primary_color and analyze_image and product.get('image'):
        primary_color = extract_color_from_image(product['image'])

    # Body type suitability
    suitable_body_types = get_suitable_body_types(
        name_result['category'],
        product.get('name', ''),
        primary_color
    )

    classification = {
        'category': name_result['category'],
        'occasions': name_result['occasions'],
        'styles': name_result['styles'],
        'primary_color': primary_color or 'unknown',
        'suitable_body_types': suitable_body_types,
        'fashion_tags': extract_fashion_tags(product.get('name', '')),
    }

    return {**product, 'classification': classification}


def get_suitable_body_types(category: str, name: str, color: str) -> list:
    """Xác định body type phù hợp dựa trên category và đặc điểm sản phẩm"""
    name_lower = name.lower()
    suitable = []

    if category in BODY_TYPE_RECOMMENDATIONS:
        cat_rules = BODY_TYPE_RECOMMENDATIONS[category]
        for body_type, fitting_keywords in cat_rules.items():
            if any(kw in name_lower for kw in fitting_keywords):
                suitable.append(body_type)

    # Nếu không match gì → phù hợp với tất cả
    return suitable if suitable else ['HOURGLASS', 'PEAR', 'INVERTED_TRIANGLE', 'RECTANGLE', 'APPLE']


def extract_fashion_tags(name: str) -> list:
    """Trích xuất fashion tags từ tên"""
    tags = []
    name_lower = name.lower()
    tag_keywords = {
        'oversized': ['oversized', 'oversize', 'rộng', 'loose', 'baggy'],
        'fitted': ['ôm', 'slim', 'fitted', 'skinny', 'body'],
        'high-waist': ['cạp cao', 'high waist', 'high-waist', 'lưng cao'],
        'crop': ['crop', 'ngắn', 'cắt'],
        'patterned': ['họa tiết', 'kẻ sọc', 'hoa', 'caro', 'stripe', 'floral'],
        'solid': ['trơn', 'solid', 'plain', 'basic'],
        'dark-tone': ['tối màu', 'đen', 'navy', 'dark', 'nâu', 'tím than'],
        'light-tone': ['sáng màu', 'pastel', 'nhạt', 'trắng', 'kem', 'nude'],
    }
    for tag, keywords in tag_keywords.items():
        if any(kw in name_lower for kw in keywords):
            tags.append(tag)
    return tags


# ─── BATCH CLASSIFY TOÀN BỘ SẢN PHẨM ───────────────────────────────────────
def batch_classify(products: list, analyze_images: bool = True) -> list:
    """Classify nhiều sản phẩm — sequential (SQLite không hỗ trợ parallel write)"""
    results = []
    total = len(products)

    for i, product in enumerate(products):
        classified = classify_product(product, analyze_image=analyze_images)
        results.append(classified)
        if (i + 1) % 10 == 0:
            print(f'[Classifier] Processed {i+1}/{total}')

    return results


# ─── LƯU CLASSIFICATION VÀO SQLITE ──────────────────────────────────────────
def save_classifications(classified_products: list, db_path: str = None):
    if db_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(base_dir, '..', 'database', 'database_v2.db'))
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Thêm cột nếu chưa có
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN category TEXT")
        cursor.execute("ALTER TABLE products ADD COLUMN classification TEXT")
    except Exception:
        pass  # Cột đã tồn tại

    for p in classified_products:
        cls = p.get('classification', {})
        cursor.execute('''
            UPDATE products SET
                category = ?,
                classification = ?
            WHERE id = ?
        ''', (
            cls.get('category', 'UNKNOWN'),
            json.dumps(cls, ensure_ascii=False),
            p['id']
        ))

    conn.commit()
    conn.close()
    return len(classified_products)


# ─── ADMIN: SHOP PROFILE ─────────────────────────────────────────────────────
def build_shop_profile(shop_id: str, db_path: str = None) -> dict:
    """Tạo profile shop từ sản phẩm đã classify — dùng cho AI Recommend Shop"""
    if db_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(base_dir, '..', 'database', 'database_v2.db'))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE shop_id = ? AND classification IS NOT NULL",
        (shop_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {}

    products = [dict(r) for r in rows]
    classifications = [json.loads(p['classification']) for p in products]

    # Thống kê
    all_styles = [s for cls in classifications for s in cls.get('styles', [])]
    all_occasions = [o for cls in classifications for o in cls.get('occasions', [])]
    categories = [cls.get('category') for cls in classifications]
    prices = [p['price'] for p in products if p['price']]

    style_counts = Counter(all_styles)
    cat_counts = Counter(categories)
    total = len(products)

    return {
        'shop_id': shop_id,
        'total_products': total,
        'top_styles': [s for s, _ in style_counts.most_common(3)],
        'occasions_covered': list(set(all_occasions)),
        'category_distribution': {
            cat: round(count / total, 2) for cat, count in cat_counts.items()
        },
        'price_min': min(prices) if prices else 0,
        'price_max': max(prices) if prices else 0,
        'price_avg': round(sum(prices) / len(prices)) if prices else 0,
        'completeness_score': calculate_completeness(cat_counts),
    }


def calculate_completeness(cat_counts: Counter) -> float:
    """Score 0-1: shop có đủ category để tạo full outfit không"""
    has_top = 'TOP' in cat_counts
    has_bottom = 'BOTTOM' in cat_counts
    has_dress = 'DRESS' in cat_counts
    has_shoes = 'SHOES' in cat_counts
    has_accessory = 'ACCESSORY' in cat_counts

    score = 0
    if has_top or has_dress: score += 0.3
    if has_bottom or has_dress: score += 0.3
    if has_shoes: score += 0.25
    if has_accessory: score += 0.15
    return round(score, 2)


# ─── ADMIN: SHOP MAPPING ─────────────────────────────────────────────────────
def map_all_shops(db_path: str = None) -> dict:
    """Map tất cả shops theo category — dùng cho Admin Shop Mapping"""
    if db_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(base_dir, '..', 'database', 'database_v2.db'))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT shop_id FROM products WHERE shop_id IS NOT NULL")
    shop_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    mapping = {
        'FULL_OUTFIT': [],
        'TOP_SPECIALIST': [],
        'BOTTOM_SPECIALIST': [],
        'DRESS_SPECIALIST': [],
        'SHOES_SPECIALIST': [],
        'ACCESSORY_SPECIALIST': [],
    }

    for shop_id in shop_ids:
        profile = build_shop_profile(shop_id, db_path)
        if not profile:
            continue

        cat_dist = profile.get('category_distribution', {})
        completeness = profile.get('completeness_score', 0)

        if completeness >= 0.6:
            mapping['FULL_OUTFIT'].append(profile)
        else:
            # Tìm category dominant (>50%)
            dominant = max(cat_dist.items(), key=lambda x: x[1], default=(None, 0))
            if dominant[1] >= 0.5:
                key = f"{dominant[0]}_SPECIALIST"
                if key in mapping:
                    mapping[key].append(profile)

    return mapping
