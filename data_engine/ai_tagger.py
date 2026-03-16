import os
import sqlite3
import requests
import numpy as np
import colorsys
from PIL import Image
from io import BytesIO
from sklearn.cluster import KMeans

# Configuration for color detection
COLOR_RANGES = [
    # (H_min, H_max, S_min, V_min, Name) - S and V are 0-100
    (0, 10, 20, 35, "đỏ"),
    (350, 360, 20, 35, "đỏ"),
    (10, 25, 20, 35, "cam"),
    (25, 65, 20, 35, "vàng"),
    (65, 150, 20, 35, "xanh lá"),
    (150, 200, 20, 35, "xanh dương"),
    (200, 260, 20, 35, "xanh dương"),
    (260, 290, 20, 35, "tím"),
    (290, 350, 20, 35, "hồng"),
]

def rgb_to_name(r, g, b):
    rf, gf, bf = r/255.0, g/255.0, b/255.0
    h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
    h_deg = h * 360
    s_pct = s * 100
    v_pct = v * 100
    
    # Neutrals
    if s_pct < 20:
        if v_pct > 85: return "trắng"
        if v_pct < 35: return "đen"
        return "xám"
    
    # Earthy/Beige
    if 20 <= s_pct <= 50 and 60 <= v_pct <= 95:
        if 20 <= h_deg <= 50: return "be"
    if 20 <= s_pct <= 70 and 20 <= v_pct <= 50:
        if 10 <= h_deg <= 40: return "nâu"
        
    for h_min, h_max, s_min, v_min, name in COLOR_RANGES:
        if h_min <= h_deg <= h_max:
            if name == "xanh dương" and v_pct < 45: return "xanh navy"
            return name
            
    return "đa sắc"

def detect_color(image_path_or_url):
    """
    Phát hiện màu chính, màu phụ, mã hex và tông màu từ ảnh.
    """
    try:
        if not image_path_or_url:
            return "không xác định", None, "#CCCCCC", "Neutral"

        img = None
        if isinstance(image_path_or_url, str) and image_path_or_url.startswith("http"):
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(image_path_or_url, headers=headers, timeout=10)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
        else:
            if os.path.exists(image_path_or_url):
                img = Image.open(image_path_or_url).convert("RGB")
            else:
                # Fallback if path is relative or missing
                return "không xác định", None, "#CCCCCC", "Neutral"
            
        # Resize để xử lý nhanh
        img = img.resize((100, 100))
        img_np = np.array(img)
        pixels = img_np.reshape(-1, 3)
        
        # Lọc bỏ pixel nền trắng/xám sáng
        mask = ~((pixels[:, 0] > 230) & (pixels[:, 1] > 230) & (pixels[:, 2] > 230))
        fg_pixels = pixels[mask]
        
        if len(fg_pixels) < 50:
            return "trắng", None, "#FFFFFF", "Neutral"
            
        # K-Means clustering
        n_clusters = 3
        kmeans = KMeans(n_clusters=n_clusters, n_init='auto', random_state=42).fit(fg_pixels)
        colors = kmeans.cluster_centers_.astype(int)
        labels = kmeans.labels_
        counts = np.bincount(labels)
        
        order = np.argsort(counts)[::-1]
        c1 = colors[order[0]]
        p1 = counts[order[0]] / len(fg_pixels)
        
        c2 = colors[order[1]] if len(order) > 1 else None
        p2 = (counts[order[1]] / len(fg_pixels)) if len(order) > 1 else 0
        
        hex_primary = '#{:02x}{:02x}{:02x}'.format(*c1).upper()
        
        # Logic chọn màu chính/phụ
        if p1 > 0.3 and p2 > 0.3:
            # Nếu 2 màu đều chiếm tỷ trọng lớn và khác nhau rõ rệt
            if np.linalg.norm(c1 - c2) > 80:
                color_primary = "Multicolor"
            else:
                color_primary = rgb_to_name(*c1)
        else:
            color_primary = rgb_to_name(*c1)
            
        color_secondary = rgb_to_name(*c2) if c2 is not None and p2 > 0.2 else None
        
        # Xác định color_tone
        rf, gf, bf = c1/255.0
        h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
        
        tone = "Neutral"
        if s > 0.75:
            tone = "Bright"
        elif color_primary in ["đỏ", "cam", "vàng", "hồng"]:
            tone = "Warm"
        elif color_primary in ["xanh dương", "xanh lá", "tím", "xanh navy"]:
            tone = "Cool"
        elif color_primary in ["đen", "trắng", "xám", "be", "nâu"]:
            tone = "Neutral"
            
        return color_primary, color_secondary, hex_primary, tone
        
    except Exception as e:
        print(f"[Tagger] Error in detect_color: {e}")
        return "không xác định", None, "#CCCCCC", "Neutral"

def tag_from_name(product_name):
    """
    Gán nhãn dựa trên từ khóa trong tên sản phẩm.
    """
    name = (product_name or "").lower()
    
    # Gender
    gender = "Female" # Default
    if any(k in name for k in ["nam", "men", "boy", "male"]):
        gender = "Male"
    if any(k in name for k in ["unisex", "đôi", "couple"]):
        gender = "Unisex"
    if any(k in name for k in ["nữ", "women", "girl", "female", "ladies"]):
        gender = "Female"
        
    # Fit Type
    fit = "Regular fit"
    if any(k in name for k in ["oversized", "rộng", "form rộng", "baggy", "loose"]):
        fit = "Oversized"
    elif any(k in name for k in ["slim", "ôm", "body", "skinny", "fitted"]):
        fit = "Slim fit"
        
    # Season
    season = "All-season"
    if any(k in name for k in ["hè", "mùa hè", "summer", "thoáng mát", "linen", "cotton mỏng"]):
        season = "Summer"
    elif any(k in name for k in ["đông", "thu đông", "winter", "len", "dày", "ấm", "nỉ"]):
        season = "Winter"
    elif any(k in name for k in ["thu", "xuân", "spring", "fall"]):
        season = "Spring-Fall"
        
    # Occasion
    occasion = "Daily wear"
    if any(k in name for k in ["công sở", "văn phòng", "office", "work", "công ty"]):
        occasion = "Work"
    elif any(k in name for k in ["thể thao", "sport", "gym", "yoga", "running"]):
        occasion = "Sport"
    elif any(k in name for k in ["dạ tiệc", "party", "sự kiện", "event", "dự tiệc"]):
        occasion = "Party"
        
    return {
        "gender": gender,
        "fit_type": fit,
        "season": season,
        "occasion": occasion
    }

def tag_product(item_id, image_path, image_url, product_name):
    """
    Gộp tag từ ảnh và tên.
    """
    # Ưu tiên path local nếu có
    primary, secondary, hex_code, tone = detect_color(image_path or image_url)
    tags = tag_from_name(product_name)
    
    return {
        "color_primary": primary,
        "color_secondary": secondary,
        "hex_primary": hex_code,
        "color_tone": tone,
        **tags
    }

def batch_tag_from_db(db_path, limit=100, overwrite=False):
    """
    Quét DB và gán nhãn cho các sản phẩm.
    """
    if not os.path.exists(db_path):
        print(f"[Tagger] DB not found: {db_path}")
        return 0
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Lấy các cột mới để kiểm tra xem đã được gán chưa
    query = "SELECT id, item_id, name, image_url, clean_image_path FROM products"
    conditions = []
    if not overwrite:
        # Giả định color_primary là cột đại diện
        conditions.append("(color_primary IS NULL OR color_primary = '')")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += f" LIMIT {limit}"
    
    rows = cur.execute(query).fetchall()
    if not rows:
        conn.close()
        return 0
        
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"[Tagger] Tagging {len(rows)} products...")
    success_count = 0
    
    for i, row in enumerate(rows):
        cid = row['id']
        name = row['name']
        url = row['image_url']
        clean_rel_path = row['clean_image_path']
        
        # Chuyển clean_rel_path thành path tuyệt đối để detect_color
        clean_abs_path = None
        if clean_rel_path:
            clean_abs_path = os.path.join(project_root, "frontend", clean_rel_path.lstrip('/'))
            # Nếu đường dẫn trong DB có chữ 'static/' ở đầu nhưng static folder config là 'frontend'
            # thì phải điều chỉnh. 
            # Giả định clean_rel_path = 'static/clean_images/xxx.png'
            # Path thực tế: frontend/static/clean_images/xxx.png
            if not os.path.exists(clean_abs_path):
                # Thử lại nếu không tìm thấy
                clean_abs_path = os.path.join(project_root, "frontend", clean_rel_path)

        res = tag_product(row['item_id'], clean_abs_path, url, name)
        
        cur.execute("""
            UPDATE products SET
                color_primary = ?,
                color_secondary = ?,
                hex_primary = ?,
                color_tone = ?,
                gender = ?,
                fit_type = ?,
                season = ?,
                occasion = ?
            WHERE id = ?
        """, (
            res['color_primary'],
            res['color_secondary'],
            res['hex_primary'],
            res['color_tone'],
            res['gender'],
            res['fit_type'],
            res['season'],
            res['occasion'],
            cid
        ))
        
        success_count += 1
        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"[Tagger] Tagged {i+1}/{len(rows)}...")
            
    conn.commit()
    conn.close()
    print(f"[Tagger] Finished. Tagged {success_count} products.")
    return success_count

if __name__ == "__main__":
    # Determine the base directory (assuming we are in data_engine/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "database", "database_v2.db")
    batch_tag_from_db(DB_PATH, limit=5)
