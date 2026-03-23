import os
import uuid
import requests as _req
import unicodedata
from flask import current_app

def _norm_ascii(s: str) -> str:
    """Chuẩn hóa chuỗi tiếng Việt sang ASCII không dấu, xử lý ký tự đ."""
    if not s: return ""
    s = s.lower().strip()
    # Normalize to NFD and filter out combining marks
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd').replace('Đ', 'd')

def infer_canonical_category_by_name(name: str) -> tuple[str, str]:
    """Phân loại sản phẩm dựa trên tên (One-pieces, Bottoms, Tops)."""
    n = _norm_ascii(name)
    
    # Rule 1: Ưu tiên nhận diện Váy/Đầm/Jumpsuit là 'one-pieces'
    if any(k in n for k in ["dam", "dress", "vay lien", "jumpsuit", "set vay", "bodysuit", "vay kieu", "vay tre vai", "vay xoe", "vay body"]):
        if "chan vay" not in n:
            return "one-pieces", "dress"
    
    # Rule 2: Chân váy hoặc Quần là 'bottoms'
    if any(k in n for k in ["chan vay", "skirt"]):
        return "bottoms", "skirt"
    if any(k in n for k in ["jean", "denim"]):
        return "bottoms", "jeans"
    if any(k in n for k in ["quan tay", "trouser", "quan au", "quan dai", "quan baggy", "quan ong suong", "quan jogger"]):
        return "bottoms", "trousers"
    if any(k in n for k in ["short", "quan dui", "shorts"]):
        return "bottoms", "shorts"
    if "quan" in n:
        return "bottoms", "trousers"

    # Rule 3: Còn lại là 'tops'
    if any(k in n for k in ["croptop", "crop top", "crop", "ao ho eo", "baby tee"]):
        return "tops", "crop_top"
    if any(k in n for k in ["tshirt", "t-shirt", "tee", "ao thun", "ao phong", "ao canh"]):
        return "tops", "t_shirt"
    if "so mi" in n or "shirt" in n or "ao kieu" in n:
        return "tops", "shirt"
    if any(k in n for k in ["hoodie", "sweater", "ao len", "cardigan"]):
        return "tops", "sweater"
    if any(k in n for k in ["khoac", "jacket", "blazer", "coat", "gi le"]):
        return "tops", "jacket"
    
    # Rule 4: Fallback cho "vay" (không phải chân váy)
    if "vay" in n and "chan vay" not in n:
        return "one-pieces", "dress"

    return "tops", "t_shirt"

def map_category_to_fashn(db_category: str) -> str:
    """Map category từ database sang format Fashn VTON 1.5."""
    if not db_category:
        return "tops"
    cat = str(db_category).lower().strip()
    
    # Rule 1: Đầm/Váy liền
    if any(k in cat for k in ["one-pieces", "dress", "jumpsuit", "romper", "đầm", "váy liền", "dam", "bodysuit"]):
        if "chan vay" not in cat and "skirt" not in cat:
            return "one-pieces"
    
    # Rule 2: Váy (không phải chân váy)
    if "vay" in cat and "chan vay" not in cat and "skirt" not in cat:
        return "one-pieces"

    # Rule 3: Quần/Chân váy
    if any(k in cat for k in ["bottoms", "bottom", "quan", "quần", "jeans", "pants", "trousers", "shorts", "skirt", "chan vay"]):
        return "bottoms"
        
    return "tops"

def download_garment_image(image_url: str, shopee_url: str):
    """
    Download hoặc lấy ảnh garment từ local. Thử image_url trước, nếu lỗi thử shopee_url.
    Trả về đường dẫn file local (tuyệt đối), hoặc None nếu hoàn toàn thất bại.
    """
    save_dir = os.path.join(current_app.static_folder, 'uploads', 'tryon')
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    os.makedirs(save_dir, exist_ok=True)

    # TRƯỜNG HỢP 1: image_url là đường dẫn nội bộ (bắt đầu bằng /)
    if image_url and image_url.startswith("/"):
        # Chuyển đổi từ /uploads/abc.png thành đường dẫn tuyệt đối trên đĩa
        # Lưu ý: current_app.static_folder trỏ đến thư mục 'frontend'
        local_path = os.path.join(current_app.static_folder, image_url.lstrip("/"))
        if os.path.exists(local_path):
            # Tạo một bản copy vào thư mục tryon để xử lý, tránh ghi đè ảnh gốc
            ext = os.path.splitext(local_path)[1] or ".png"
            new_path = os.path.join(save_dir, f"garment_{uuid.uuid4().hex}{ext}")
            import shutil
            shutil.copy(local_path, new_path)
            return new_path

    # TRƯỜNG HỢP 2: image_url là URL từ Shopee/Lazada hoặc nguồn bên ngoài
    urls_to_try = []
    if image_url and image_url.startswith("http"):
        urls_to_try.append(image_url)
    if shopee_url and shopee_url.startswith("http"):
        urls_to_try.append(shopee_url)

    for url in urls_to_try:
        try:
            resp = _req.get(url, timeout=12, headers=headers, allow_redirects=True)
            ct   = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and len(resp.content) > 1000 and "image" in ct:
                ext = ".jpg"
                if "png" in ct:  ext = ".png"
                if "webp" in ct: ext = ".webp"
                filename = f"garment_{uuid.uuid4().hex}{ext}"
                path = os.path.join(save_dir, filename)
                
                with open(path, "wb") as f:
                    f.write(resp.content)
                return path
        except Exception:
            continue
    return None
