import os
import sqlite3
import urllib.request
import numpy as np
from PIL import Image
import io
import colorsys
import unicodedata
from sklearn.cluster import KMeans

def _remove_accents(s):
    if not s:
        return ""
    # Normalize unicode characters
    s = str(s).replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFD', s)
    # Remove accent marks
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower()

def rgb_to_name(r, g, b):
    # Scale to 0-1 for colorsys
    rf, gf, bf = r/255.0, g/255.0, b/255.0
    h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
    
    # Scale to 0-360, 0-100, 0-100 as per guide
    h_deg = h * 360
    s_pct = s * 100
    v_pct = v * 100
    
    # If S < 15: xét V -> trang (V > 80), xam (V 30–80), den (V < 30)
    if s_pct < 15:
        if v_pct > 80: return "trang"
        if v_pct > 30: return "xam"
        return "den"
    
    # Nếu S < 40 và V 55–80: be
    if s_pct < 40 and 55 <= v_pct <= 80:
        return "be"
    
    # Nếu S < 40 và V < 55: nau
    if s_pct < 40 and v_pct < 55:
        return "nau"
    
    # Nếu S >= 15: xét H
    if s_pct >= 15:
        # 0–15 hoặc 345–360: do
        if h_deg <= 15 or h_deg >= 345: return "do"
        # 15–40: cam
        if 15 < h_deg <= 40: return "cam"
        # 40–70: vang
        if 40 < h_deg <= 70: return "vang"
        # 70–150: xanh la
        if 70 < h_deg <= 150: return "xanh la"
        # 150–200: xanh duong nhat
        if 150 < h_deg <= 200: return "xanh duong nhat"
        # 200–260: xanh duong (nếu V < 40 thì: xanh navy)
        if 200 < h_deg <= 260:
            if v_pct < 40: return "xanh navy"
            return "xanh duong"
        # 260–290: tim
        if 260 < h_deg <= 290: return "tim"
        # 290–345: hong
        if 290 < h_deg < 345: return "hong"
        
    return "unknown"

def get_color_from_image(image_url):
    try:
        # 1. Tải ảnh
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(image_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        
        img = Image.open(io.BytesIO(data)).convert("RGB")
        
        # 2. Chuẩn bị pixel
        img = img.resize((100, 100))
        pixels = np.array(img).reshape(-1, 3)
        
        # Lọc bỏ pixel nền: R > 220 and G > 220 and B > 220
        # Lọc bỏ pixel đen: R < 15 and G < 15 and B < 15
        mask = ~((pixels[:, 0] > 220) & (pixels[:, 1] > 220) & (pixels[:, 2] > 220))
        mask &= ~((pixels[:, 0] < 15) & (pixels[:, 1] < 15) & (pixels[:, 2] < 15))
        
        filtered_pixels = pixels[mask]
        
        if len(filtered_pixels) < 50:
            filtered_pixels = pixels # Dùng toàn bộ nếu lọc quá tay
            
        # 3. Chạy K-Means
        kmeans = KMeans(n_clusters=3, n_init=5, random_state=0)
        kmeans.fit(filtered_pixels)
        
        labels = kmeans.labels_
        centers = kmeans.cluster_centers_
        
        unique_labels, counts = np.unique(labels, return_counts=True)
        # Sắp xếp giảm dần theo số pixel
        sorted_indices = np.argsort(counts)[::-1]
        
        best_label = sorted_indices[0]
        color_primary_rgb = centers[best_label].astype(int)
        
        color_secondary_rgb = None
        p2_pct = 0
        if len(sorted_indices) > 1:
            second_label = sorted_indices[1]
            color_secondary_rgb = centers[second_label].astype(int)
            p2_pct = counts[second_label] / len(labels)
            
        primary_name = rgb_to_name(*color_primary_rgb)
        secondary_name = rgb_to_name(*color_secondary_rgb) if color_secondary_rgb is not None else None
        
        # 5. Xác định Multicolor: Nếu màu chính và màu phụ khác nhau và cluster thứ 2 chiếm > 20%
        final_primary = primary_name
        if secondary_name and primary_name != secondary_name and p2_pct > 0.20:
            final_primary = "Multicolor"
            
        # 6. Xác định color_tone
        tone = "Neutral"
        neutral_colors = ["den", "trang", "xam", "be", "nau", "kem"]
        warm_colors = ["do", "cam", "vang", "hong"]
        cool_colors = ["xanh la", "xanh duong", "xanh navy", "xanh duong nhat", "tim"]
        
        # Guide: Bright nếu S > 75 bất kể màu gì
        # Re-calc HSV for primary
        ph = colorsys.rgb_to_hsv(color_primary_rgb[0]/255.0, color_primary_rgb[1]/255.0, color_primary_rgb[2]/255.0)
        if ph[1] * 100 > 75:
            tone = "Bright"
        elif primary_name in warm_colors:
            tone = "Warm"
        elif primary_name in cool_colors:
            tone = "Cool"
        elif primary_name in neutral_colors:
            tone = "Neutral"
            
        return {
            "color_primary": final_primary,
            "color_secondary": secondary_name,
            "hex_primary": '#{:02x}{:02x}{:02x}'.format(*color_primary_rgb).upper(),
            "color_tone": tone
        }
        
    except Exception as e:
        print(f"[Tagger] Error processing image {image_url}: {e}")
        return {}

def get_labels_from_name(product_name):
    name = _remove_accents(product_name)
    
    # gender
    gender = "Female" # Default
    if any(k in name for k in ["nu", "women", "girl", "female", "ladies", "lady"]):
        gender = "Female"
    elif any(k in name for k in ["nam", "men", "boy", "male"]):
        gender = "Male"
    elif any(k in name for k in ["unisex", "doi", "couple"]):
        gender = "Unisex"
        
    # fit_type
    fit = "Regular fit"
    if any(k in name for k in ["oversized", "rong", "form rong", "baggy", "loose", "thung"]):
        fit = "Oversized"
    elif any(k in name for k in ["slim", "om", "body", "skinny", "fitted", "bo"]):
        fit = "Slim fit"
        
    # season
    season = "All-season"
    if any(k in name for k in ["he", "mua he", "summer", "thoan mat", "mong", "lua", "lanh"]):
        season = "Summer"
    elif any(k in name for k in ["dong", "thu dong", "winter", "len", "day", "am", "ni"]):
        season = "Winter"
    elif any(k in name for k in ["thu", "xuan", "spring", "fall"]):
        season = "Spring-Fall"
        
    # occasion
    occasion = "Daily wear"
    if any(k in name for k in ["cong so", "van phong", "office", "work", "cong ty", "business"]):
        occasion = "Work"
    elif any(k in name for k in ["the thao", "sport", "gym", "yoga", "running", "training"]):
        occasion = "Sport"
    elif any(k in name for k in ["da tiec", "party", "su kien", "event", "du tiec", "diec"]):
        occasion = "Party"
        
    return {
        "gender": gender,
        "fit_type": fit,
        "season": season,
        "occasion": occasion
    }

def tag_all_products(db_path, limit=100):
    if not os.path.exists(db_path):
        print(f"[Tagger] WARNING: DB not found at {db_path}")
        return 0
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 2. Kiểm tra cột
    cur.execute("PRAGMA table_info(products)")
    existing_cols = [row[1] for row in cur.fetchall()]
    required_cols = ["color_primary", "color_secondary", "hex_primary", "color_tone", "gender", "fit_type", "season", "occasion"]
    
    missing = [c for c in required_cols if c not in existing_cols]
    if missing:
        print(f"[Tagger] WARNING: Missing columns in products table: {missing}")
        # Tự động thêm nếu thiếu (theo logic "Lỗi thường gặp")
        for col in missing:
            try:
                cur.execute(f"ALTER TABLE products ADD COLUMN {col} TEXT")
                print(f"[Tagger] Added missing column: {col}")
            except Exception as e:
                print(f"[Tagger] Failed to add column {col}: {e}")
    
    # 3. Query items
    query = """
        SELECT id, item_id, name, image_url 
        FROM products 
        WHERE image_url IS NOT NULL AND image_url != ''
        AND (color_primary IS NULL OR color_primary = '')
        LIMIT ?
    """
    rows = cur.execute(query, (limit,)).fetchall()
    
    if not rows:
        conn.close()
        return 0
        
    print(f"[Tagger] Processing {len(rows)} products...")
    processed_count = 0
    
    for i, row in enumerate(rows):
        res_color = get_color_from_image(row['image_url'])
        res_labels = get_labels_from_name(row['name'])
        
        # Merge dicts
        tags = {**res_color, **res_labels}
        
        # Nếu color_primary vẫn trống (lỗi tải ảnh), đánh dấu là "unknown" để không query lại
        if not tags.get('color_primary'):
            tags['color_primary'] = 'unknown'
            
        update_query = """
            UPDATE products SET
                color_primary = ?, color_secondary = ?, hex_primary = ?, color_tone = ?,
                gender = ?, fit_type = ?, season = ?, occasion = ?
            WHERE id = ?
        """
        cur.execute(update_query, (
            tags.get('color_primary'), tags.get('color_secondary'), tags.get('hex_primary'), tags.get('color_tone'),
            tags.get('gender'), tags.get('fit_type'), tags.get('season'), tags.get('occasion'),
            row['id']
        ))
        
        processed_count += 1
        
        # In tiến độ: [Tagger] 15/40 — ao thun | den | Female | Regular fit
        print(f"[Tagger] {processed_count}/{len(rows)} — {row['name'][:20]} | {tags.get('color_primary')} | {tags.get('gender')} | {tags.get('fit_type')}")
        
        # Commit every 10
        if processed_count % 10 == 0:
            conn.commit()
            
    conn.commit()
    conn.close()
    return processed_count
