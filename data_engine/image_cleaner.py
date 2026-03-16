import os
import sqlite3
import requests
import numpy as np
from PIL import Image
from io import BytesIO

def clean_product_image(image_url, item_id, output_dir):
    """
    Tải ảnh từ image_url, phát hiện ảnh ghép, crop ô tốt nhất, resize 512x512 PNG.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    file_name = f"{item_id}.png"
    file_path = os.path.join(output_dir, file_name)
    
    try:
        # Tải ảnh
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://shopee.vn/'
        }
        response = requests.get(image_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[Cleaner] Failed to download {image_url}: {response.status_code}")
            return None
            
        img = Image.open(BytesIO(response.content)).convert("RGB")
        
        # Chuyển sang grayscale để tính toán
        img_gray = img.convert("L")
        img_np = np.array(img_gray)
        h, w = img_np.shape
        
        # Logic phát hiện ảnh ghép: Tính tổng pixel theo hàng và cột
        # Ở đây dùng độ thay đổi trung bình của cột/hàng
        row_means = np.mean(img_np, axis=1)
        col_means = np.mean(img_np, axis=0)
        
        row_diffs = np.abs(np.diff(row_means))
        col_diffs = np.abs(np.diff(col_means))
        
        # Ngưỡng phát hiện vạch chia (thay đổi đột ngột > 60% so với trung bình diff)
        # Hoặc dùng một ngưỡng cố định dựa trên quan sát ảnh Shopee
        # Thường vạch chia là các đường thẳng tắp có giá trị trung bình khác hẳn
        
        def find_split_indices(diffs, size):
            threshold = np.mean(diffs) * 4 # Heuristic threshold
            splits = np.where(diffs > threshold)[0]
            if len(splits) == 0: return []
            
            # Lọc các index quá gần nhau (ví dụ vạch dày vài pixel)
            filtered = [splits[0]]
            for s in splits[1:]:
                if s - filtered[-1] > size // 5: # Vạch phải cách nhau ít nhất 20% kích thước ảnh
                    filtered.append(s)
            return filtered

        h_splits = find_split_indices(row_diffs, h) # Đường cắt ngang -> chia hàng
        v_splits = find_split_indices(col_diffs, w) # Đường cắt dọc -> chia cột
        
        num_rows = len(h_splits) + 1
        num_cols = len(v_splits) + 1
        
        # Nếu là ảnh đơn, giữ nguyên. Nếu là ảnh ghép, chọn ô tốt nhất.
        if num_rows > 1 or num_cols > 1:
            best_tile = None
            max_std = -1
            
            # Chia thành grid
            tile_h = h // num_rows
            tile_w = w // num_cols
            
            for r in range(num_rows):
                for c in range(num_cols):
                    left = c * tile_w
                    top = r * tile_h
                    right = left + tile_w
                    bottom = top + tile_h
                    
                    # Thêm một chút padding vào trong để tránh vạch chia
                    tile = img.crop((left + 2, top + 2, right - 2, bottom - 2))
                    # Tính độ lệch chuẩn pixel để chọn ô rõ nhất (không phải màu trơn hoặc logo)
                    tile_std = np.std(np.array(tile.convert("L")))
                    
                    if tile_std > max_std:
                        max_std = tile_std
                        best_tile = tile
            img = best_tile

        # Chuẩn hóa: Resize về 512x512, giữ tỉ lệ, đặt lên nền trắng
        img.thumbnail((512, 512), Image.LANCZOS)
        final_img = Image.new("RGB", (512, 512), (255, 255, 255))
        w_small, h_small = img.size
        final_img.paste(img, ((512 - w_small) // 2, (512 - h_small) // 2))
        
        final_img.save(file_path, "PNG")
        # Trả về đường dẫn mà frontend có thể truy cập
        return f"static/clean_images/{file_name}"
        
    except Exception as e:
        print(f"[Cleaner] Error cleaning {item_id}: {e}")
        return None

def batch_clean_from_db(db_path, limit=100, overwrite=False):
    """
    Quét DB, tải và làm sạch ảnh cho các sản phẩm chưa có clean_image_path.
    """
    if not os.path.exists(db_path):
        print(f"[Cleaner] DB not found: {db_path}")
        return 0
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Query các item cần xử lý
    query = "SELECT id, item_id, image_url FROM products"
    conditions = []
    if not overwrite:
        conditions.append("(clean_image_path IS NULL OR clean_image_path = '')")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += f" LIMIT {limit}"
    
    rows = cur.execute(query).fetchall()
    if not rows:
        conn.close()
        return 0
        
    # Determine the base directory (assuming we are in data_engine/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Save in frontend folder so Flask can serve it (since static_folder=frontend)
    SAVE_DIR = os.path.join(BASE_DIR, "frontend", "static", "clean_images")
    DB_PATH = os.path.join(BASE_DIR, "database", "database_v2.db")
    output_dir = SAVE_DIR
    
    print(f"[Cleaner] Processing {len(rows)} images...")
    success_count = 0
    
    for i, row in enumerate(rows):
        cid = row['id']
        item_id = row['item_id']
        url = row['image_url']
        
        if not url: continue
        
        clean_path = clean_product_image(url, item_id, output_dir)
        if clean_path:
            cur.execute("UPDATE products SET clean_image_path = ? WHERE id = ?", (clean_path, cid))
            success_count += 1
            
        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"[Cleaner] Handled {i+1}/{len(rows)}...")
            
    conn.commit()
    conn.close()
    print(f"[Cleaner] Finished. Cleaned {success_count} images.")
    return success_count

if __name__ == "__main__":
    # Test script
    import sys
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "database_v2.db"))
    batch_clean_from_db(db_file, limit=5)
