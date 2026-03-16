import csv
import io
import os
import time
import requests
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    send_from_directory,
    session,
)
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import (
    Category,
    Color,
    ItemType,
    Occasion,
    Outfit,
    Product,
    Season,
    Style,
    User,
)
from .ai.pose import extract_keypoints
from .ai.features import compute_ratios, estimate_gender
from .ai.classifier import predict_shape, predict_shape_with_confidence
from .ai.image_tools import remove_background_rgba, recolor_clothing, upscale_image, change_background, detect_clothing_color
import json as _json

def is_single_item_image(image_bytes: bytes) -> bool:
    """
    Checks if an image contains only one person.
    This is a proxy for identifying single-item product images.
    """
    try:
        people, error = extract_keypoints(image_bytes, max_people=2)
        if error:
            # If pose detection fails, conservatively assume it's a single item
            return True
        # The image is valid if it contains exactly one person
        return len(people) == 1
    except Exception:
        # In case of any unexpected error, assume valid to avoid blocking products
        return True


# Add project root to path to import data_engine
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import crawlers independently
try:
    from data_engine.shopee_crawler import crawl_shop as crawl_shopee_new, save_products_to_db
    from data_engine.product_classifier import batch_classify, save_classifications, build_shop_profile, map_all_shops
except ImportError as e:
    print(f"Could not import new crawlers/classifiers: {str(e).encode('ascii', 'ignore').decode('ascii')}")

try:
    from data_engine.crawler.shopee import crawl_shop_url as crawl_shopee
except ImportError as e:
    print(f"Could not import shopee crawler: {str(e).encode('ascii', 'ignore').decode('ascii')}")
    def crawl_shopee(url, limit=50): return []

try:
    from data_engine.crawler.lazada import crawl_lazada_shop_url as crawl_lazada
except ImportError as e:
    # Lazada is optional
    def crawl_lazada(url, limit=50): return []

CRAWLER_AVAILABLE = True # Always True now since we use requests


main_bp = Blueprint('main', __name__)

# ──────────────────────────────────────────────────────────────────────────────
# Canonical clothing taxonomy (for AI training)
# ──────────────────────────────────────────────────────────────────────────────

# Map từ ai_category (FeatureExtractor) → (main_group, sub_category) theo schema bạn đưa
CANONICAL_CLOTHING_MAP = {
    # Tops
    "Top_Tshirt": ("tops", "t_shirt"),
    "Top_Shirt": ("tops", "shirt"),
    "Top_Tanktop": ("tops", "tank_top"),
    "Top_Croptop": ("tops", "crop_top"),
    "Top_Polo": ("tops", "shirt"),
    "Top_Sweater": ("tops", "sweater"),      # gồm cả hoodie/cardigan trong rules hiện tại
    # Outerwear (xem như tops trong schema đơn giản)
    "Outer_Blazer": ("tops", "blazer"),
    "Outer_Jacket": ("tops", "jacket"),
    "Outer_Coat": ("tops", "jacket"),
    # Bottoms
    "Bottom_Jeans": ("bottoms", "jeans"),
    "Bottom_Formal_Trousers": ("bottoms", "trousers"),
    "Bottom_Shorts": ("bottoms", "shorts"),
    "Bottom_Jogger": ("bottoms", "trousers"),
    "Bottom_Skirt": ("dresses_skirts", "skirt"),
    "Bottom_LongSkirt": ("dresses_skirts", "skirt"),
    # Dresses & one-piece
    "Dress": ("dresses_skirts", "dress"),
    "Jumpsuit": ("dresses_skirts", "dress"),
    # Sets & sleepwear
    "Set_Sleepwear": ("sleepwear_homewear", "pajama_set"),
    "Matching_set": ("clothing_sets", "top_bottom_set"),
}


def map_to_canonical_clothing(ai_category: str, item_type_raw: str, shopee_cat: str | None = None):
    """
    Map từ taxonomy AI hiện tại (ai_category, item_type) sang schema CLOTHING-ONLY bạn mô tả.
    Trả về (item_type_name, category_name) hoặc (None, None) nếu không map được.
    """
    key = (ai_category or "").strip()
    if key in CANONICAL_CLOTHING_MAP:
        return CANONICAL_CLOTHING_MAP[key]

    # Fallback nhẹ theo item_type nếu cần mở rộng sau này
    it = (item_type_raw or "").strip().lower()
    if not it:
        return None, None

    if it == "top":
        return "tops", "t_shirt"
    if it == "bottom":
        return "bottoms", "trousers"
    if it == "dress":
        return "dresses_skirts", "dress"
    if it == "set":
        return "clothing_sets", "top_bottom_set"

    return None, None

def infer_canonical_category_by_name(name: str) -> tuple[str, str]:
    n = _norm_ascii(name)
    # Heuristic keywords
    if any(k in n for k in ["croptop", "crop top", "crop", "ao ho eo", "baby tee"]):
        return "tops", "crop_top"
    if any(k in n for k in ["tshirt", "t-shirt", "tee", "ao thun", "ao phong"]):
        return "tops", "t_shirt"
    if "so mi" in n or "shirt" in n:
        return "tops", "shirt"
    if any(k in n for k in ["hoodie", "sweater", "ao len", "cardigan"]):
        return "tops", "sweater"
    if any(k in n for k in ["khoac", "jacket", "blazer", "coat"]):
        return "tops", "jacket"
    if any(k in n for k in ["chan vay", "skirt", "vay"]):
        return "dresses_skirts", "skirt"
    if any(k in n for k in ["dam", "dress", "vay lien"]):
        return "dresses_skirts", "dress"
    if any(k in n for k in ["jean", "denim"]):
        return "bottoms", "jeans"
    if any(k in n for k in ["quan tay", "trouser", "quan au"]):
        return "bottoms", "trousers"
    if any(k in n for k in ["short", "quan dui", "shorts"]):
        return "bottoms", "shorts"
    # Default safe
    return "tops", "t_shirt"

def _norm_text(s: str, max_len: int | None = None) -> str:
    t = (s or "").strip()
    t = " ".join(t.split())
    if max_len is not None:
        return t[:max_len]
    return t

def _norm_ascii(s: str) -> str:
    try:
        import unicodedata
        s2 = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("ascii")
        return " ".join(s2.lower().split())
    except Exception:
        return " ".join((s or "").lower().split())

def _parse_vnd_price(val) -> int:
    try:
        if isinstance(val, (int, float)):
            return int(round(float(val)))
        s = str(val or "").strip()
        if not s:
            return 0
        import re as _re
        # Find all number-like tokens (allow thousand separators and ranges)
        tokens = _re.findall(r"\d[\d\.\,]*", s)
        nums = []
        for t in tokens:
            digits = _re.sub(r"[^\d]", "", t)
            if digits:
                try:
                    nums.append(int(digits))
                except Exception:
                    pass
        if nums:
            # Choose the minimum price when a range is provided
            return min(nums)
        # Fallback: strip non-digits globally
        digits_all = _re.sub(r"[^0-9]", "", s)
        if digits_all:
            return int(digits_all)
        return 0
    except Exception:
        return 0

def _derive_item_id_from_payload(data: dict) -> int:
    import re as _re
    raw = data.get('item_id')
    if raw is not None:
        try:
            return int(str(raw).strip())
        except Exception:
            pass
    link = data.get('shopee_link') or data.get('product_url') or ''
    if link:
        m = _re.search(r'/product/\d+/(\d+)', link)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        # As a stable numeric fallback from URL
        try:
            import zlib
            return int(zlib.adler32(link.encode('utf-8')) & 0x7FFFFFFF)
        except Exception:
            pass
    # Last resort: from name
    name = str(data.get('name') or '')
    if name:
        try:
            import zlib
            return int(zlib.adler32(name.encode('utf-8')) & 0x7FFFFFFF)
        except Exception:
            pass
    return int(datetime.utcnow().timestamp())

def _download_image_to_uploads(img_url: str) -> str | None:
    try:
        if not img_url or not (img_url.startswith("http://") or img_url.startswith("https://")):
            return None
        import urllib.request as _u
        import mimetypes
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        low = img_url.lower()
        if "shopee" in low or "susercontent" in low:
            headers["Referer"] = "https://shopee.vn/"
        if "lazada" in low or "lzdcdn" in low or "alicdn" in low:
            headers["Referer"] = "https://www.lazada.vn/"
        req = _u.Request(img_url, headers=headers)
        with _u.urlopen(req, timeout=10) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
        ext = None
        if ctype:
            ext = mimetypes.guess_extension(ctype.split(";")[0].strip())
        if not ext:
            if low.endswith(".png"):
                ext = ".png"
            elif low.endswith(".webp"):
                ext = ".webp"
            else:
                ext = ".jpg"
        upload_folder = os.path.join(current_app.static_folder, "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        fname = f"prod_{int(time.time()*1000)}{ext}"
        fpath = os.path.join(upload_folder, fname)
        with open(fpath, "wb") as f:
            f.write(data)
        return f"/uploads/{fname}"
    except Exception:
        return None

def _fetch_remote_image(url: str) -> bytes | None:
    try:
        import urllib.request
        headers = {"User-Agent": "Mozilla/5.0"}
        low = str(url).lower()
        if 'shopee' in low or 'susercontent' in low or 'cf.shopee.vn' in low:
            headers["Referer"] = "https://shopee.vn/"
        if 'lazada' in low or 'lzdcdn' in low or 'alicdn' in low:
            headers["Referer"] = "https://www.lazada.vn/"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            return resp.read()
    except Exception:
        return None

def _crop_bottom_center(img_bytes: bytes) -> bytes | None:
    try:
        from PIL import Image
        import io as _io
        im = Image.open(_io.BytesIO(img_bytes)).convert("RGB")
        w, h = im.size
        x0 = int(w * 0.2)
        x1 = int(w * 0.8)
        y0 = int(h * 0.55)
        y1 = int(h * 0.95)
        box = (max(0, x0), max(0, y0), min(w, x1), min(h, y1))
        crop = im.crop(box)
        out = _io.BytesIO()
        crop.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return None

def _select_variant_image(item: dict) -> str:
    raw_img = (item.get('image_url') or item.get('image') or '').strip()
    images_all = item.get('images_all') or item.get('images') or []
    var_color = item.get('variant_color') or item.get('color')
    def _full(u: str) -> str:
        if not u: return ''
        if u.startswith('http'): return u
        if u.startswith('/'): return u
        return f"https://cf.shopee.vn/file/{u}"
    def _hsv_stats(img_bytes: bytes):
        try:
            from PIL import Image
            import io as _io
            import numpy as _np
            im = Image.open(_io.BytesIO(img_bytes)).convert("HSV")
            w, h = im.size
            center = im.crop((w//6, h//6, 5*w//6, 5*h//6))
            arr = _np.array(center).astype(_np.float32)
            h_arr = arr[...,0] / 255.0
            s_arr = arr[...,1] / 255.0
            v_arr = arr[...,2] / 255.0
            return float(h_arr.mean()), float(s_arr.mean()), float(v_arr.mean())
        except Exception:
            return 0.0, 0.0, 0.0
    def _score_target(cname: str, h: float, s: float, v: float, target: str) -> float:
        if cname == target:
            return 100.0
        t = (target or "").strip()
        # Neutral heuristics first
        if t == "Black":
            base = 80.0 if (v < 0.35 and s < 0.25) else (60.0 if v < 0.45 and s < 0.20 else 20.0)
            return base
        if t == "White":
            base = 80.0 if (s < 0.12 and v > 0.65) else (60.0 if s < 0.18 and v > 0.55 else 20.0)
            return base
        if t == "Gray":
            base = 70.0 if s < 0.18 else 20.0
            return base
        # Hue-based rough bands
        hue = h * 360.0
        def _band(lo, hi): 
            return 75.0 if (s > 0.15 and lo <= hue <= hi) else 25.0
        if t == "Blue":
            return _band(190, 250)
        if t == "Green":
            return _band(80, 160)
        if t == "Purple":
            return _band(260, 310)
        if t == "Pink":
            return _band(310, 360)
        if t == "Red":
            return _band(0, 25)
        if t == "Orange":
            return _band(25, 45)
        if t == "Brown":
            # Brown ~ dark orange
            return 70.0 if (25 <= hue <= 50 and s > 0.15 and 0.25 < v < 0.75) else 25.0
        if t == "Beige":
            return 70.0 if (25 <= hue <= 55 and s < 0.20 and v > 0.55) else 25.0
        # Default low score
        return 15.0
    if var_color and images_all:
        target = normalize_color(var_color, None)[0]
        candidates = [_full(raw_img)] + [_full(v) for v in images_all]
        seen = set()
        best_c, best_score = "", -1.0
        for c in candidates:
            if not c or c in seen: 
                continue
            seen.add(c)
            data = _fetch_remote_image(c)
            if not data:
                continue
            try:
                cname, _ct = detect_clothing_color(data)
            except Exception:
                cname = "Multicolor"
            h,s,v = _hsv_stats(data)
            score = _score_target(cname, h, s, v, target)
            if cname == "Multicolor":
                score *= 0.2
            if score > best_score:
                best_score, best_c = score, c
        if best_c:
            return best_c
    # Fallback: choose first non-Multicolor candidate from images_all
    for v in images_all:
        c = _full(v)
        data = _fetch_remote_image(c)
        if not data:
            continue
        try:
            cname, _ct = detect_clothing_color(data)
            if cname and cname != "Multicolor":
                return c
        except Exception:
            continue
    return _full(raw_img)
def _finalize_gender(initial: str, item_type_name: str | None, category_name: str | None, product_name: str | None) -> str:
    g = (initial or "Unisex").strip()
    it = (item_type_name or "").strip().lower()
    cat = _norm_ascii(category_name or "")
    name_norm = _norm_ascii(product_name or "")
    female_cats = {"crop_top", "dress", "skirt", "blouse", "camisole", "tube_top", "off_shoulder", "bralette", "babydoll", "peplum"}
    female_substrings = [
        "crop", "dress", "skirt", "blouse", "camisole", "tube", "off shoulder",
        "tre vai", "tay bong", "yem", "hai day", "2 day", "bodycon",
        "babydoll", "peplum", "co tim", "ren", "phoi ren", "kem no", "no", "beo", "beo gau", "xinh xan", "de thuong", "long vu", "nu tinh", "danh nu"
    ]
    female_tokens = [
        "nu", "nư", "women", "girl", "lady", "dam", "vay", "croptop", "crop top", "hai day", "2 day", "yem",
        "skirt", "dress", "jumpsuit", "blouse", "camisole", "tube top", "off shoulder", "bralette", "babydoll", "peplum",
        "co tim", "ren", "phoi ren", "kem no", "no", "beo", "beo gau", "xinh xan", "de thuong", "long vu", "nu tinh", "danh nu"
    ]
    male_tokens = ["nam", "men", "male", "boy", "gentleman"]
    if (cat.replace(" ", "_") in female_cats) or any(sub in cat for sub in female_substrings) or any(tok in name_norm for tok in female_tokens):
        return "Female"
    if g.lower() == "unisex" and any(tok in name_norm for tok in male_tokens):
        return "Male"
    return g

_COLOR_MAP = {
    "đen": "Black", "black": "Black",
    "trắng": "White", "white": "White",
    "xám": "Gray", "ghi": "Gray", "gray": "Gray",
    "be": "Beige", "beige": "Beige", "kem": "Beige",
    "nâu": "Brown", "brown": "Brown",
    "xanh lá": "Green", "xanh lả": "Green", "green": "Green",
    "xanh dương": "Blue", "xanh biển": "Blue", "blue": "Blue",
    "đỏ": "Red", "red": "Red",
    "vàng": "Yellow", "yellow": "Yellow",
    "hồng": "Pink", "pink": "Pink",
    "tím": "Purple", "purple": "Purple",
    "cam": "Orange", "orange": "Orange",
    "đa sắc": "Multicolor", "nhiều màu": "Multicolor", "đủ màu": "Multicolor", "du mau": "Multicolor",
    "multicolor": "Multicolor", "pattern": "Multicolor", "hoa": "Multicolor", "caro": "Multicolor", "sọc": "Multicolor"
}

def normalize_color(color_raw: str | None, tone_raw: str | None) -> tuple[str, str]:
    cr = _norm_text(str(color_raw or ""), 50).lower()
    name = _COLOR_MAP.get(cr, None)
    if not name:
        if any(k in cr for k in ["multi", "pattern", "print", "caro", "hoa", "sọc"]):
            name = "Multicolor"
        elif cr:
            name = cr.title()
        else:
            name = "Multicolor"
    tr = _norm_text(str(tone_raw or ""), 20).lower()
    if not tr:
        if name in ("White", "Black", "Gray", "Beige"):
            tone = "Neutral"
        elif name in ("Brown", "Beige"):
            tone = "Earthy"
        elif name == "Multicolor":
            tone = "Pattern"
        else:
            tone = "Neutral"
    else:
        tone = tr.title()
    return name, tone

_GENDER_MAP = {
    "nam": "Male", "male": "Male",
    "nữ": "Female", "nu": "Female", "female": "Female",
    "unisex": "Unisex", "cặp": "Unisex", "cap": "Unisex"
}

def normalize_gender(raw: str | None) -> str:
    r = _norm_text(str(raw or ""), 20).lower()
    if not r:
        return "Unisex"
    return _GENDER_MAP.get(r, r.title())

_FIT_MAP = {
    "regular": "Regular fit", "regular fit": "Regular fit",
    "slim": "Slim fit", "skinny": "Slim fit",
    "oversize": "Oversize", "oversized": "Oversize", "loose": "Oversize", "relaxed": "Oversize",
    "bodycon": "Bodycon", "tight": "Bodycon"
}

def normalize_fit_type(raw: str | None) -> str:
    r = _norm_text(str(raw or ""), 50).lower()
    if not r:
        return "Regular fit"
    return _FIT_MAP.get(r, r.title())

_MATERIAL_MAP = {
    "cotton": "Cotton", "thun": "Cotton",
    "polyester": "Polyester", "poly": "Polyester",
    "denim": "Denim", "jean": "Denim", "jeans": "Denim",
    "leather": "Leather", "da": "Leather",
    "linen": "Linen", "đũi": "Linen", "dui": "Linen",
    "silk": "Silk", "lụa": "Silk", "lua": "Silk",
    "wool": "Wool", "len": "Wool",
    "nylon": "Nylon", "nilon": "Nylon"
}

def normalize_material(raw: str | None) -> str:
    r = _norm_text(str(raw or ""), 100).lower()
    if not r:
        return "Other"
    for k, v in _MATERIAL_MAP.items():
        if k in r:
            return v
    return r.title()

_STYLE_MAP = {
    "casual": "Casual", "basic": "Casual", "đơn giản": "Casual",
    "street": "Streetwear", "streetwear": "Streetwear",
    "formal": "Formal", "công sở": "Formal", "office": "Formal",
    "sport": "Sporty", "athleisure": "Sporty",
    "minimal": "Minimalist", "tối giản": "Minimalist",
    "vintage": "Vintage"
}

def normalize_style(raw: str | None) -> str:
    r = _norm_text(str(raw or ""), 50).lower()
    if not r:
        return "Casual"
    return _STYLE_MAP.get(r, r.title())

_SEASON_MAP = {
    "summer": "Summer", "hè": "Summer",
    "winter": "Winter", "đông": "Winter",
    "spring": "Spring", "xuân": "Spring",
    "autumn": "Autumn", "fall": "Autumn", "thu": "Autumn",
    "all": "All-season"
}

def normalize_season(raw: str | list | None) -> str:
    if isinstance(raw, list) and raw:
        s = str(raw[0])
    else:
        s = str(raw or "")
    r = _norm_text(s, 50).lower()
    if not r:
        return "All-season"
    for k, v in _SEASON_MAP.items():
        if k in r:
            return v
    return r.title()

_OCCASION_MAP = {
    "daily": "Daily wear", "hàng ngày": "Daily wear", "di hàng ngày": "Daily wear",
    "work": "Work", "office": "Work", "công sở": "Work",
    "party": "Party", "tiệc": "Party",
    "formal": "Formal event", "sự kiện": "Formal event",
    "outdoor": "Outdoor", "du lịch": "Outdoor",
    "gym": "Gym", "thể thao": "Gym", "sport": "Gym"
}

def normalize_occasion(raw: str | list | None) -> str:
    if isinstance(raw, list) and raw:
        s = str(raw[0])
    else:
        s = str(raw or "")
    r = _norm_text(s, 50).lower()
    if not r:
        return "Daily wear"
    for k, v in _OCCASION_MAP.items():
        if k in r:
            return v
    return r.title()

def normalize_product_fields(item: dict) -> dict:
    gender = normalize_gender(item.get("gender"))
    material = normalize_material(item.get("material"))
    fit_type = normalize_fit_type(item.get("fit_type"))
    base_color_raw = item.get("variant_color") or item.get("color")
    color_name, color_tone = normalize_color(base_color_raw, item.get("color_tone"))
    style_name = normalize_style(item.get("style"))
    season_name = normalize_season(item.get("season"))
    occasion_name = normalize_occasion(item.get("occasion"))
    details = _norm_text(item.get("details") or "", 200)
    name_norm = _norm_ascii(str(item.get("name") or ""))
    sub_cat_norm = _norm_ascii(str(item.get("sub_category") or ""))

    if gender.lower() == "unisex":
        female_tokens = ["nu", "nư", "women", "girl", "lady", "dam", "vay", "croptop", "crop top", "hai day", "2 day", "yem", "skirt", "dress", "jumpsuit", "blouse", "camisole", "tube top", "off shoulder", "bralette", "babydoll", "peplum", "tre vai", "tay bong", "bodycon", "co tim", "ren", "phoi ren", "kem no", "no", "beo", "beo gau", "xinh xan", "de thuong", "long vu", "nu tinh", "danh nu"]
        male_tokens = ["nam", "men", "male", "boy", "gentleman"]
        female_subcats = {"crop_top", "dress", "skirt", "blouse", "camisole", "tube_top", "off_shoulder", "bralette", "babydoll", "peplum"}
        if any(tok in name_norm for tok in female_tokens) or (sub_cat_norm.replace(" ", "_") in female_subcats) or any(sub in sub_cat_norm for sub in ["crop","dress","skirt","blouse","camisole","tube","off shoulder","tre vai","tay bong","yem","hai day","2 day","bodycon","babydoll","peplum","co tim","ren","phoi ren","kem no","no","beo","beo gau","xinh xan","de thuong","long vu","nu tinh","danh nu"]):
            gender = "Female"
        elif any(tok in name_norm for tok in male_tokens):
            gender = "Male"
    img_url = item.get("image_url") or item.get("image")
    img_bytes = None
    if img_url:
        try:
            import urllib.request
            headers = {"User-Agent": "Mozilla/5.0"}
            low = str(img_url).lower()
            if 'shopee' in low or 'susercontent' in low or 'cf.shopee.vn' in low:
                headers["Referer"] = "https://shopee.vn/"
            if 'lazada' in low or 'lzdcdn' in low or 'alicdn' in low:
                headers["Referer"] = "https://www.lazada.vn/"
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                img_bytes = resp.read()
        except Exception:
            img_bytes = None
    if img_bytes:
        try:
            cname, ctone = detect_clothing_color(img_bytes)
            # Only override with image detection when we don't have a reliable variant color
            base_has_color = bool(_norm_text(str(base_color_raw or ""), 50))
            base_is_multi = _norm_text(str(base_color_raw or ""), 50).lower() in ("multicolor", "đa sắc", "nhiều màu", "đủ màu", "du mau")
            if not base_has_color or base_is_multi:
                # Robust neutral fix: if image overall saturation is very low, force neutral colors
                try:
                    from PIL import Image
                    import io as _io
                    im = Image.open(_io.BytesIO(img_bytes)).convert("HSV")
                    w, h = im.size
                    center = im.crop((w//6, h//6, 5*w//6, 5*h//6))
                    import numpy as _np
                    arr = _np.array(center)
                    sat = arr[...,1].astype(_np.float32)/255.0
                    val = arr[...,2].astype(_np.float32)/255.0
                    s_med = float(_np.median(sat))
                    v_med = float(_np.median(val))
                    if s_med < 0.15:
                        if v_med > 0.6:
                            color_name = "White"; color_tone = "Neutral"
                        elif v_med < 0.35:
                            color_name = "Black"; color_tone = "Neutral"
                        else:
                            color_name = "Gray"; color_tone = "Neutral"
                    else:
                        if cname:
                            color_name = cname
                        if ctone:
                            color_tone = ctone
                except Exception:
                    if cname:
                        color_name = cname
                    if ctone:
                        color_tone = ctone
        except Exception:
            pass

    # STICKY PATTERN CHECK: If name explicitly says stripes/pattern, override color detection.
    # We do this at the end so it's the final authority.
    if any(k in name_norm for k in ["soc", "caro", "hoa tiet", "print", "pattern", "floral", "ke soc", "ke vach"]):
        color_name = "Multicolor"
        color_tone = "Pattern"
        if gender == "Unisex":
            try:
                pts, err = extract_keypoints(img_bytes)
                if not err and pts:
                    ratios = compute_ratios(pts)
                    glabel, gconf = estimate_gender(ratios)
                    strong_female = any(x in name_norm for x in ["dam","vay","croptop","crop top","hai day","2 day","yem","skirt","dress","jumpsuit","blouse","camisole","tube top","off shoulder","bralette","babydoll","peplum","tre vai","tay bong","bodycon","co tim","ren","phoi ren","kem no","no","beo","beo gau","xinh xan","de thuong","long vu","nu tinh","danh nu"]) or (sub_cat_norm.replace(" ", "_") in {"crop_top","dress","skirt","blouse","camisole","tube_top","off_shoulder","bralette","babydoll","peplum"})
                    if glabel in ("Male", "Female") and gconf >= 0.7:
                        if strong_female and glabel == "Male":
                            pass
                        else:
                            gender = glabel
            except Exception:
                pass
    if gender == "Unisex":
        try:
            from data_engine.feature_engine import FeatureExtractor
            name_text = str(item.get("name") or "")
            sh_cat = str(item.get("category") or "")
            feats = FeatureExtractor.extract(name_text, sh_cat)
            g2 = feats.get("gender")
            if g2 and g2 != "Unisex":
                gender = g2
        except Exception:
            pass
    return {
        "gender": gender,
        "material": material,
        "fit_type": fit_type,
        "color_name": color_name,
        "color_tone": color_tone,
        "style_name": style_name,
        "season_name": season_name,
        "occasion_name": occasion_name,
        "details": details
    }

def get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance

# --- Serve Frontend Routes ---
@main_bp.route('/')
def serve_index():
    return send_from_directory(current_app.static_folder, 'index.html')

@main_bp.route('/<path:path>')
def serve_static(path):
    return send_from_directory(current_app.static_folder, path)

# --- API Routes ---

@main_bp.route('/api/image-proxy')
def image_proxy():
    try:
        src = request.args.get('url') or ''
        if not src or not (src.startswith('http://') or src.startswith('https://')):
            return jsonify({'message': 'invalid url'}), 400
        import urllib.request as _u
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        low = src.lower()
        if 'shopee' in low or 'susercontent' in low:
            headers["Referer"] = "https://shopee.vn/"
        if 'lazada' in low or 'lzdcdn' in low or 'alicdn' in low:
            headers["Referer"] = "https://www.lazada.vn/"
        req = _u.Request(src, headers=headers)
        with _u.urlopen(req, timeout=8) as resp:
            data = resp.read()
            ctype = resp.headers.get('Content-Type', '')
            if not ctype:
                if src.endswith('.png'):
                    ctype = 'image/png'
                elif src.endswith('.jpg') or src.endswith('.jpeg'):
                    ctype = 'image/jpeg'
                elif src.endswith('.webp'):
                    ctype = 'image/webp'
                else:
                    ctype = 'application/octet-stream'
            return Response(data, mimetype=ctype)
    except Exception as e:
        return jsonify({'message': f'proxy error: {str(e)}'}), 502

@main_bp.route('/api/classify', methods=['POST'])
def classify_by_name():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'message': 'name required'}), 400
    try:
        from data_engine.feature_engine import FeatureExtractor
        feats = FeatureExtractor.extract(name, '')
        ai_category = feats.get('category', 'Other')
        ai_item_type = feats.get('item_type', '')
        it_name, sub_cat = map_to_canonical_clothing(ai_category=ai_category, item_type_raw=ai_item_type)
        return jsonify({
            'ai_item_type': ai_item_type,
            'ai_category': ai_category,
            'item_type': it_name,
            'category': sub_cat
        }), 200
    except Exception as e:
        return jsonify({'message': f'classification error: {e}'}), 500

@main_bp.route('/api/analyze-proportion', methods=['POST'])
def analyze_proportion():
    if 'image' not in request.files:
        return jsonify({'message': 'image required'}), 400
    image = request.files['image'].read()
    points_list, err = extract_keypoints(image)
    if err == "mediapipe_missing":
        return jsonify({'message': 'mediapipe not installed'}), 501
    if err == "no_pose" or not points_list:
        return jsonify({'message': 'pose not detected'}), 422
    if err and err.startswith("mediapipe_error:"):
        return jsonify({'message': err}), 500
    
    # Use the first person detected
    points = points_list[0]
    ratios = compute_ratios(points)
    
    # Check for manual gender preference
    pref_gender = request.form.get('gender')
    gender_label, gender_conf = estimate_gender(ratios)
    if pref_gender and pref_gender != 'auto':
        gender_label = pref_gender.capitalize()
        gender_conf = 1.0
        
    return jsonify({'ratios': ratios, 'gender': gender_label, 'gender_confidence': gender_conf}), 200

@main_bp.route('/api/identify-body-shape', methods=['POST'])
def identify_body_shape():
    if 'image' not in request.files:
        return jsonify({'message': 'image required'}), 400
    image = request.files['image'].read()
    points_list, err = extract_keypoints(image)
    if err == "mediapipe_missing":
        return jsonify({'message': 'mediapipe not installed'}), 501
    if err == "no_pose" or not points_list:
        return jsonify({'message': 'pose not detected'}), 422
    if err and err.startswith("mediapipe_error:"):
        return jsonify({'message': err}), 500
    
    # Use the first person detected
    points = points_list[0]
    ratios = compute_ratios(points)
    
    # Check for manual gender preference
    pref_gender = request.form.get('gender')
    gender_label, gender_conf = estimate_gender(ratios)
    if pref_gender and pref_gender != 'auto':
        gender_label = pref_gender.capitalize()
        gender_conf = 1.0
    # Basic prediction
    try:
        shape, conf, source = predict_shape_with_confidence(ratios)
    except Exception:
        shape = predict_shape(ratios)
        conf = 0.6
        source = "rule_fallback"

    response_data = {
        'body_shape': shape, 
        'confidence': conf, 
        'source': source, 
        'ratios': ratios, 
        'gender': gender_label, 
        'gender_confidence': gender_conf
    }

    # ADVANCED 3D & LLM MODE
    if request.form.get('advanced') == 'true':
        try:
            # Proxy request to the advanced pipeline service (port 5000)
            # Reset file pointer for the next read
            request.files['image'].seek(0)
            advanced_res = requests.post(
                'http://127.0.0.1:5000/api/ai/advanced/analyze',
                files={'image': (request.files['image'].filename, request.files['image'].read(), request.files['image'].content_type)},
                timeout=15 # Don't wait too long if LLM is slow
            )
            if advanced_res.status_code == 200:
                adv_data = advanced_res.json()
                # Merge advanced results: 3D measurements and LLM stylistic advice
                response_data['advanced_analysis'] = adv_data.get('analysis')
                response_data['style_recommendations'] = adv_data.get('style_recommendations')
                # If advanced classifier is better, we can also override shape/gender
                if adv_data.get('analysis', {}).get('body_shape'):
                    response_data['body_shape'] = adv_data['analysis']['body_shape']
                    response_data['source'] = 'advanced_3d_pipeline'
        except Exception as e:
            response_data['advanced_error'] = f"Advanced service unavailable: {str(e)}"

    return jsonify(response_data), 200

@main_bp.route('/api/products/reinfer_gender', methods=['POST'])
def reinfer_gender_batch():
    try:
        data = request.json or {}
        ids = data.get('ids')
        q = Product.query
        if ids and ids != 'ALL':
            try:
                q = q.filter(Product.id.in_(ids))
            except Exception:
                pass
        products = q.all()
        updated = 0
        for p in products:
            it_name = p.item_type.name if p.item_type else p.category_label
            cat_name = p.category.name if p.category else p.sub_category_label
            g0 = _finalize_gender(p.gender or 'Unisex', it_name, cat_name, p.name)
            gnew = g0
            if gnew == 'Unisex':
                img_bytes = None
                img_url = p.image_url or ''
                try:
                    if img_url.startswith('/uploads/'):
                        fpath = os.path.join(current_app.static_folder, img_url.lstrip('/'))
                        if os.path.exists(fpath):
                            with open(fpath, 'rb') as f:
                                img_bytes = f.read()
                    elif img_url.startswith('http'):
                        import urllib.request as _u
                        headers = {"User-Agent": "Mozilla/5.0"}
                        low = img_url.lower()
                        if 'shopee' in low or 'susercontent' in low:
                            headers["Referer"] = "https://shopee.vn/"
                        if 'lazada' in low or 'lzdcdn' in low or 'alicdn' in low:
                            headers["Referer"] = "https://www.lazada.vn/"
                        req = _u.Request(img_url, headers=headers)
                        with _u.urlopen(req, timeout=6) as resp:
                            img_bytes = resp.read()
                except Exception:
                    img_bytes = None
                if img_bytes:
                    try:
                        pts, err = extract_keypoints(img_bytes)
                        if not err and pts:
                            ratios = compute_ratios(pts)
                            glabel, gconf = estimate_gender(ratios)
                            name_norm = _norm_ascii(p.name or '')
                            strong_female = any(x in name_norm for x in ["dam","vay","croptop","crop top","hai day","2 day","yem","skirt","dress","jumpsuit"]) or ((cat_name or '').replace(' ','_').lower() in {"crop_top","dress","skirt"})
                            if glabel in ("Male", "Female") and gconf >= 0.7:
                                if strong_female and glabel == "Male":
                                    pass
                                else:
                                    gnew = glabel
                    except Exception:
                        pass
            if gnew != (p.gender or ''):
                p.gender = gnew
                updated += 1
        db.session.commit()
        return jsonify({'message': 'Re-inferred genders', 'updated': updated, 'total': len(products)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Reinfer error: {str(e)}'}), 500
@main_bp.route('/api/ai/status', methods=['GET'])
def ai_status():
    import sys as _sys
    import os as _os
    status = {
        'python_executable': _sys.executable,
        'python_version': _sys.version,
        'cwd': _os.getcwd(),
        'mediapipe_installed': False,
        'mediapipe_version': None
    }
    try:
        import mediapipe as mp  # type: ignore
        status['mediapipe_installed'] = True
        try:
            import importlib.metadata as ilmd  # py3.8+
            status['mediapipe_version'] = ilmd.version('mediapipe')
        except Exception:
            status['mediapipe_version'] = getattr(mp, '__version__', None)
    except Exception:
        status['mediapipe_installed'] = False
    return jsonify(status), 200

@main_bp.route('/api/remove-bg', methods=['POST'])
def remove_bg():
    if 'image' not in request.files:
        return jsonify({'message': 'image required'}), 400
    try:
        img_bytes = request.files['image'].read()
        result = remove_background_rgba(img_bytes)
        if isinstance(result, tuple) and len(result) == 2:
            out_bytes, mime = result
        else:
            out_bytes, mime = result, "image/png"
        return Response(out_bytes, mimetype=mime)
    except RuntimeError as e:
        if str(e) == "mediapipe_missing":
            return jsonify({'message': 'mediapipe not installed'}), 501
        return jsonify({'message': f'processing error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'message': f'error: {str(e)}'}), 500
@main_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    print(f"\n=== REGISTRATION ATTEMPT ===")
    print(f"Username: {str(data.get('username')).encode('ascii', 'ignore').decode('ascii')}")
    print(f"Email: {str(data.get('email')).encode('ascii', 'ignore').decode('ascii')}")
    print(f"Phone: {str(data.get('phone')).encode('ascii', 'ignore').decode('ascii')}")
    
    # Clean input
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip() if data.get('phone') else ''
    password = data.get('password', '').strip()
    
    # Check if user already exists
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        print(f"ERROR: User already exists - {str(existing_user.username).encode('ascii', 'ignore').decode('ascii')}")
        return jsonify({'message': 'User already exists'}), 400
    
    try:
        hashed_pw = generate_password_hash(password)
        print(f"Password hashed successfully")
        desired_role = str(data.get('role', 'USER')).upper()
        # Only allow creating non-USER roles if current session user is ADMIN
        can_set_role = False
        sid = session.get('user_id')
        if sid:
            admin_user = User.query.get(sid)
            if admin_user and admin_user.role == 'ADMIN':
                can_set_role = True
        final_role = desired_role if (desired_role != 'USER' and can_set_role) else 'USER'

        new_user = User(
            username=username,
            email=email,
            phone=phone,
            password=hashed_pw,
            role=final_role,
            status='Active',
            fullname=data.get('fullname', username).strip(), # Use provided fullname or fallback to username
            avatar = f"https://ui-avatars.com/api/?name={username}&background=FF9EB5&color=fff",
            created_at=datetime.utcnow()
        )
                
        db.session.add(new_user)
        db.session.commit()
        
        print(f"✅ USER CREATED SUCCESSFULLY:")
        print(f"   - ID: {new_user.id}")
        print(f"   - Username: {new_user.username}")
        print(f"   - Role: {new_user.role}")
        print(f"   - Status: {new_user.status}")
        print(f"=========================\n")
        
        return jsonify({'message': 'Registered successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ REGISTRATION ERROR: {str(e)}")
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500


@main_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_input = data.get('login_input', '').strip()
    password = data.get('password', '').strip()
    
    print(f"DEBUG LOGIN Attempt: Input='{login_input}', PwLen={len(password)}")
    
    user = User.query.filter(
        (User.username == login_input) | 
        (User.email == login_input) |
        (User.phone == login_input)
    ).first()
    
    if user:
        print(f"DEBUG: User found: {user.username}, ID: {user.id}")
        if check_password_hash(user.password, password):
             # Improved Status Check (Handle None/Null/Case)
             user_status = str(user.status).strip().lower() if user.status else 'active'
             if user_status != 'active':
                 return jsonify({'message': 'Your account has been blocked. Please contact admin.'}), 403

             session['user_id'] = user.id
             return jsonify({
                'message': 'Login successful', 
                'role': user.role, 
                'username': user.username,
                'fullname': user.fullname,
                'user_id': user.id,
                'avatar': user.avatar,
                'email': user.email,
                'phone': user.phone,
                'address': user.address,
                'gender': user.gender,
                'dob': user.dob
            }), 200
        else:
             return jsonify({'message': 'Invalid password. Please try again.'}), 401
    
    return jsonify({'message': 'The account does not exist. Please log in again.'}), 404

@main_bp.route('/api/profile', methods=['GET', 'POST', 'PUT'])
def profile():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'message': 'Missing user_id'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        return jsonify({
            'success': True,
            'profile': {
                'id': user.id,
                'user_id': user.id, 
                'username': user.username,
                'email': user.email,
                'fullname': user.fullname,
                'phone': user.phone,
                'address': user.address,
                'gender': user.gender,
                'dob': user.dob,
                'avatar': user.avatar,
                'role': user.role
            }
        }), 200

    # POST/PUT
    user_id = None
    data = {}
    
    if request.is_json:
        data = request.json
        user_id = data.get('user_id')
    else:
        user_id = request.form.get('user_id')
        data = request.form

    if not user_id:
        return jsonify({'message': 'Unauthorized'}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    if 'fullname' in data: user.fullname = data['fullname']
    if 'email' in data: user.email = data['email']
    if 'phone' in data: user.phone = data['phone']
    if 'address' in data: user.address = data['address']
    if 'gender' in data: user.gender = data['gender']
    if 'dob' in data: user.dob = data['dob']
    
    # Handle File Upload
    if 'avatar_file' in request.files:
        file = request.files['avatar_file']
        if file.filename != '':
            # We serve static from frontend/
            upload_folder = os.path.join(current_app.static_folder, 'uploads')
            
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filename = f"avatar_{user_id}_{int(time.time())}.png"
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Since we serve root from frontend, URL is /uploads/filename
            user.avatar = f"/uploads/{filename}"

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Database commit failed'}), 500
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'profile': {
            'id': user.id,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'fullname': user.fullname,
            'phone': user.phone,
            'address': user.address,
            'gender': user.gender,
            'dob': user.dob,
            'avatar': user.avatar,
            'role': user.role
        }
    }), 200

@main_bp.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    user_list = []
    for u in users:
        # Check if status/created_at attributes exist (migration safety)
        status = getattr(u, 'status', 'Active')
        created = getattr(u, 'created_at', None)
        created_str = created.strftime('%Y-%m-%d') if created else '2025-01-01'

        user_list.append({
            'id': u.id,
            'username': u.username,
            'fullname': u.fullname,
            'email': u.email,
            'role': u.role,
            'status': status,
            'created_at': created_str, 
            'avatar': u.avatar
        })
    return jsonify(user_list), 200

@main_bp.route('/api/users/<int:id>', methods=['PATCH', 'DELETE'])
def manage_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if request.method == 'PATCH':
        data = request.json
        if 'role' in data: user.role = data['role']
        if 'status' in data and data['status']: 
            clean_status = str(data['status']).strip()
            if clean_status: # Only update if not empty
                user.status = clean_status
        if 'fullname' in data and data['fullname']: user.fullname = data['fullname'].strip()
        if 'email' in data and data['email']: user.email = data['email'].strip()
        
        # New: Username and Password support
        if 'username' in data and data['username']: 
            clean_username = data['username'].strip()
            existing = User.query.filter(User.username == clean_username, User.id != user.id).first()
            if existing:
                return jsonify({'message': 'Username already taken'}), 400
            user.username = clean_username

        if 'password' in data and data['password']:
            clean_pw = data['password'].strip()
            if len(clean_pw) > 0:
                user.password = generate_password_hash(clean_pw)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Account updated successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Database error: {str(e)}'}), 500

    if request.method == 'DELETE':
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'message': 'User deleted'}), 200
        except:
            db.session.rollback()
            return jsonify({'message': 'Error deleting user'}), 500

@main_bp.route('/api/outfits', methods=['GET', 'POST', 'DELETE'])
def outfits():
    if request.method == 'GET':
        outfits = Outfit.query.all()
        return jsonify([{
            'id': o.id, 'name': o.name, 'image': o.image_url, 
            'style': o.style, 'shop_link': o.shop_link, 
            'body_type': o.body_type,
            'color': o.color or 'Multicolor',
            'color_tone': o.color_tone or 'Neutral'
        } for o in outfits]), 200

    if request.method == 'POST':
        data = request.json
        img_url = data.get('image')
        cname, ctone = None, None
        
        # Auto-detect color for outfits too
        if img_url:
            try:
                img_bytes = _download_image_to_uploads(img_url)[0] # This function returns (bytes, path) or (None, None)
                # Wait, _download_image_to_uploads might not be exactly what I want if I just need bytes
                # I'll use a simpler helper if available or inline it
                import urllib.request
                req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    ib = resp.read()
                    from .ai.image_tools import detect_clothing_color
                    cname, ctone = detect_clothing_color(ib)
            except Exception:
                pass

        new_outfit = Outfit(
            name=data['name'], image_url=data['image'],
            style=data['style'], shop_link=data.get('shop_link', ''),
            body_type=data.get('body_type', 'General'),
            color=cname or data.get('color', 'Multicolor'),
            color_tone=ctone or data.get('color_tone', 'Neutral')
        )
        db.session.add(new_outfit)
        db.session.commit()
        return jsonify({'message': 'Outfit added', 'color': new_outfit.color}), 201

    if request.method == 'DELETE':
        oid = request.args.get('id')
        outfit = Outfit.query.get(oid)
        if outfit:
            db.session.delete(outfit)
            db.session.commit()
            return jsonify({'message': 'Deleted'}), 200
        return jsonify({'message': 'Not found'}), 404

@main_bp.route('/api/outfits/backfill', methods=['POST'])
def outfits_backfill():
    """Analyses colors for existing outfits."""
    outfits = Outfit.query.all()
    count = 0
    from .ai.image_tools import detect_clothing_color
    import urllib.request
    
    for o in outfits:
        if not o.color or o.color == 'Multicolor':
            try:
                req = urllib.request.Request(o.image_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    ib = resp.read()
                    cname, ctone = detect_clothing_color(ib)
                    if cname:
                        o.color = cname
                        o.color_tone = ctone
                        count += 1
            except Exception:
                continue
    db.session.commit()
    return jsonify({'updated': count}), 200

@main_bp.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json
    shop_url = data.get('url')
    
    if not shop_url:
        return jsonify({'message': 'Thiếu URL'}), 400

    # Component check (optional, since we use requests now)
    pass 

    try:
        # Gọi crawler tương ứng
        current_app.logger.info(f"[CRAWL] Bắt đầu crawl: {shop_url}")
        
        if 'lazada.vn' in shop_url:
            current_app.logger.info("Detect Lazada URL")
            crawled_products = crawl_lazada(shop_url, limit=50)
        else:
            current_app.logger.info("Detect Shopee URL (or default)")
            crawled_products = crawl_shopee(shop_url, limit=50)
        
        if not crawled_products:
            return jsonify({
                'message': 'Crawl thành công nhưng không tìm thấy sản phẩm. Kiểm tra lại URL hoặc thử lại sau.',
                'products': [],
                'count': 0
            }), 200

        # Post-process images to prefer single-color variant image
        try:
            for it in crawled_products:
                it['image_url'] = _select_variant_image(it)
        except Exception:
            pass
        # Trả về dữ liệu cho frontend xem trước
        return jsonify({
            'message': 'Crawl thành công',
            'count': len(crawled_products),
            'products': crawled_products
        }), 200

    except Exception as e:
        # Ghi log lỗi chi tiết
        current_app.logger.error(f"[CRAWL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Trả về thông báo lỗi rõ ràng
        return jsonify({
            'message': f'Lỗi khi crawl: {str(e)}'
        }), 500

@main_bp.route('/api/crawl/save', methods=['POST'])
def save_crawled_products():
    data = request.json
    products_to_save = data.get('products', [])
    default_shop_name = (data.get('shop_name') or '').strip()
    default_shop_url = (data.get('shop_url') or '').strip()
    
    if not products_to_save:
        return jsonify({'message': 'No products to save'}), 400

    new_db_items = []
    saved_count = 0
    
    try:
        for item in products_to_save:
            item_id_value = item.get('variant_id') or item.get('itemid') or item.get('item_id') or item.get('itemId')
            # Ưu tiên product_url, sau đó shopee_link, cuối cùng là url (từ crawler Shopee)
            link_value = item.get('product_url') or item.get('shopee_link') or item.get('url')

            if not item_id_value and not link_value:
                continue

            item_id = str(item_id_value) if item_id_value else None

            product = None
            if item_id:
                product = Product.query.filter_by(item_id=item_id).first()
            if not product and link_value:
                product = Product.query.filter_by(product_url=link_value[:2000]).first()

            created = False
            if not product:
                if not item_id:
                    continue
                product = Product(item_id=item_id)
                db.session.add(product)
                created = True
            try:
                if item_id:
                    product.item_id = int(item_id)
            except:
                pass

            product.name = (item.get('name') or '')[:200]
            selected_img = _select_variant_image(item)
            product.image_url = selected_img[:500]
            product.product_url = (link_value or '')[:2000]

            product.price = _parse_vnd_price(item.get('price', 0))

            _norm = normalize_product_fields(item)
            product.gender = _norm["gender"][:20]
            product.material = _norm["material"][:100]
            product.fit_type = _norm["fit_type"][:50]
            product.color_tone = _norm["color_tone"][:20]
            product.details = _norm["details"]
            # Shop name resolution:
            # 1) Use provided item.shop_name
            # 2) Use request-level default_shop_name if provided
            # 3) If Shopee link with /product/<shopid>/<itemid>, label as "Shopee Shop <shopid>"
            # 4) Fallback "Shopee Store"
            resolved_shop = (item.get('shop_name') or '').strip()
            if not resolved_shop:
                resolved_shop = default_shop_name
            if not resolved_shop and link_value and 'shopee.vn' in link_value:
                import re
                m = re.search(r'/product/(\d+)/\d+', link_value)
                if m:
                    resolved_shop = f"Shopee Shop {m.group(1)}"
            if not resolved_shop and link_value and 'lazada.vn' in link_value:
                # Best-effort for Lazada: take domain prefix as label
                resolved_shop = 'Lazada Store'
            if not resolved_shop:
                resolved_shop = 'Shopee Store'
            product.shop_name = resolved_shop[:150]
            product.crawl_date = datetime.utcnow()
            product.is_active = True

            # Validate image
            if product.image_url:
                try:
                    image_bytes = requests.get(product.image_url).content
                    product.is_valid = is_single_item_image(image_bytes)
                except Exception:
                    product.is_valid = False # Mark as invalid if image can't be fetched


            # --- Category normalization for AI training ---
            # Ưu tiên map sang CLOTHING-ONLY schema (tops/bottoms/dress/sets/sleepwear)
            ai_category_val = (item.get('ai_category') or '').strip()
            item_type_raw = (item.get('item_type') or '').strip()
            sub_cat_raw = (item.get('sub_category') or '').strip()

            item_type_name, category_name = map_to_canonical_clothing(
                ai_category=ai_category_val,
                item_type_raw=item_type_raw,
                shopee_cat=item.get('category')
            )

            # Nếu không map được sang schema chuẩn → thử suy luận từ tên
            if not item_type_name or not category_name:
                try:
                    # Thử lại với FeatureExtractor nếu có
                    from data_engine.feature_engine import FeatureExtractor
                    fx = FeatureExtractor.extract(item.get('name') or '', item.get('category') or '')
                    ai_category_val = fx.get('category', ai_category_val)
                    item_type_raw = fx.get('item_type', item_type_raw)
                    item_type_name, category_name = map_to_canonical_clothing(
                        ai_category=ai_category_val,
                        item_type_raw=item_type_raw,
                        shopee_cat=item.get('category')
                    )
                except Exception:
                    pass
            # Nếu vẫn không có → heuristic theo tên để tránh "không xác định"
            if not item_type_name or not category_name:
                item_type_name, category_name = infer_canonical_category_by_name(item.get('name') or '')

            # Không còn bỏ qua vì category là bắt buộc: nếu giá trị rơi vào Other → gán về mặc định tops/t_shirt
            vn_cat = str(category_name or '').strip().lower()
            if vn_cat in ('', 'other', 'khac', 'khác', 'phan loai khac', 'phân loại khác'):
                item_type_name, category_name = 'tops', 't_shirt'

            color_name = _norm["color_name"]
            color_tone = _norm["color_tone"]
            style_name = _norm["style_name"]

            season_name = _norm["season_name"]

            occasion_name = _norm["occasion_name"]

            product.category_label = item_type_name[:50]
            product.sub_category_label = category_name[:50]
            product.color_label = color_name[:50]
            product.style_label = style_name[:50]
            product.season_label = season_name[:50]
            product.occasion_label = occasion_name[:50]

            item_type = get_or_create(ItemType, name=item_type_name)
            category = get_or_create(Category, name=category_name, defaults={"item_type": item_type})
            color = get_or_create(Color, name=color_name, defaults={"tone": color_tone})
            if color.tone != color_tone and color_tone:
                color.tone = color_tone
            style = get_or_create(Style, name=style_name)
            season = get_or_create(Season, name=season_name)
            occasion = get_or_create(Occasion, name=occasion_name)

            product.item_type = item_type
            product.category = category
            product.color = color
            product.style_ref = style
            product.season_ref = season
            product.occasion_ref = occasion

            # Finalize gender once category is known
            product.gender = _finalize_gender(product.gender, item_type_name, category_name, item.get('name'))

            if created:
                saved_count += 1
            else:
                new_db_items.append(product)

        db.session.commit()

        # Persist shop registry (name → url) for frontend listing
        try:
            registry_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'shops.json'))
            os.makedirs(os.path.dirname(registry_path), exist_ok=True)
            shops_map = {}
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    try:
                        shops_map = _json.load(f)
                    except Exception:
                        shops_map = {}
            if default_shop_name:
                # Keep first non-empty URL or update with provided default_shop_url
                current = shops_map.get(default_shop_name, {})
                cur_url = current.get('shop_url')
                new_url = default_shop_url or cur_url
                shops_map[default_shop_name] = {'shop_name': default_shop_name, 'shop_url': new_url}
            with open(registry_path, 'w', encoding='utf-8') as f:
                _json.dump(shops_map, f, ensure_ascii=False, indent=2)
        except Exception as _e:
            current_app.logger.warning(f"Shop registry update skipped: {_e}")

        return jsonify({
            'message': f'Catalog updated. Added {saved_count} new products and refreshed {len(new_db_items)} items.',
            'saved_count': saved_count,
            'updated_count': len(new_db_items)
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Save Crawl Error: {str(e).encode('ascii', 'ignore').decode('ascii')}")
        return jsonify({'message': f'Database error: {str(e)}'}), 500

@main_bp.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'GET':
        products = Product.query.order_by(Product.id.desc()).limit(100).all()
        payload = []
        for p in products:
            it_name = p.item_type.name if p.item_type else p.category_label
            cat_name = p.category.name if p.category else p.sub_category_label
            gender_disp = _finalize_gender(p.gender or 'Unisex', it_name, cat_name, p.name)
            payload.append({
                'id': p.id,
                'item_id': p.item_id,
                'name': p.name,
                'image': p.image_url,
                'price': p.price,
                'category': p.item_type.name if p.item_type else p.category_label,
                'sub_category': p.category.name if p.category else p.sub_category_label,
                'product_url': p.product_url,
                'color': p.color.name if p.color else p.color_label,
                'color_tone': p.color.tone if p.color else p.color_tone,
                'season': p.season_ref.name if p.season_ref else p.season_label,
                'occasion': p.occasion_ref.name if p.occasion_ref else p.occasion_label,
                'gender': gender_disp,
                'material': p.material,
                'style': p.style_ref.name if p.style_ref else p.style_label,
                'fit_type': p.fit_type,
                'details': p.details,
                'shop_name': p.shop_name,
            })
        return jsonify(payload), 200

    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'message': 'Missing payload'}), 400

        derived_item_id = _derive_item_id_from_payload(data)
        # Ensure uniqueness best-effort
        try:
            existing = Product.query.filter_by(item_id=derived_item_id).first()
            if existing is not None:
                from random import randint
                derived_item_id = int(f"{derived_item_id % 100000000}{randint(10,99)}")
        except Exception:
            pass

        product = Product(item_id=derived_item_id)
        product.name = (data.get('name') or '')[:200]
        raw_img = (data.get('image') or '').strip()
        saved_path = _download_image_to_uploads(raw_img) if raw_img else None
        product.image_url = (saved_path or raw_img)[:500]
        product.product_url = (data.get('product_url') or data.get('shopee_link') or '')[:2000]
        product.price = _parse_vnd_price(data.get('price', 0))
        product.shop_name = (data.get('shop_name') or 'Manual Entry')[:150]
        # For manual entry, we default to valid=True as the user is inputting it
        product.is_valid = True

        _norm = normalize_product_fields(data)
        product.gender = _norm["gender"][:20]
        product.material = _norm["material"][:100]
        product.fit_type = _norm["fit_type"][:50]
        product.color_tone = _norm["color_tone"][:20]
        product.details = _norm["details"]

        category_field = data.get('category') or 'Other'
        if isinstance(category_field, str) and '|' in category_field:
            item_type_name, sub_category_name = [part.strip() for part in category_field.split('|', 1)]
        else:
            item_type_name = str(category_field).strip() or 'Other'
            sub_category_name = (data.get('sub_category') or 'Other').strip() or 'Other'

        style_name = _norm["style_name"]
        color_name = _norm["color_name"]
        color_tone = _norm["color_tone"]
        season_name = _norm["season_name"]
        occasion_name = _norm["occasion_name"]

        product.category_label = item_type_name[:50]
        product.sub_category_label = sub_category_name[:50]
        product.color_label = color_name[:50]
        product.style_label = style_name[:50]
        product.season_label = season_name[:50]
        product.occasion_label = occasion_name[:50]

        item_type = get_or_create(ItemType, name=item_type_name)
        category = get_or_create(Category, name=sub_category_name, defaults={'item_type': item_type})
        color = get_or_create(Color, name=color_name, defaults={'tone': color_tone})
        if color.tone != color_tone and color_tone:
            color.tone = color_tone
        style = get_or_create(Style, name=style_name)
        season = get_or_create(Season, name=season_name)
        occasion = get_or_create(Occasion, name=occasion_name)

        product.item_type = item_type
        product.category = category
        product.color = color
        product.style_ref = style
        product.season_ref = season
        product.occasion_ref = occasion

        # Finalize gender using mapped category and product name
        product.gender = _finalize_gender(product.gender, item_type_name, sub_category_name, data.get('name'))

        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product added manually'}), 201

@main_bp.route('/api/products/batch_delete', methods=['POST'])
def batch_delete_products():
    data = request.json
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'message': 'No IDs provided'}), 400
        
    try:
        if ids == 'ALL':
             num_deleted = db.session.query(Product).delete()
        else:
             num_deleted = db.session.query(Product).filter(Product.id.in_(ids)).delete(synchronize_session=False)

        db.session.commit()
        return jsonify({'message': f'Deleted {num_deleted} products successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting products: {str(e)}'}), 500

@main_bp.route('/api/products/backfill_shopname', methods=['POST'])
def backfill_shopname():
    """
    One-time utility: fill missing/placeholder shop_name for Shopee/Lazada products
    based on product_url patterns. Useful when earlier saves used generic names.
    """
    try:
        import re
        updated = 0
        products = Product.query.all()
        for p in products:
            name = (p.shop_name or '').strip()
            url = p.product_url or ''
            new_name = None
            if (not name) or name in ('Shopee Store', 'Lazada Store'):
                if 'shopee.vn' in url:
                    m = re.search(r'/product/(\d+)/\d+', url)
                    if m:
                        new_name = f"Shopee Shop {m.group(1)}"
                elif 'lazada.vn' in url:
                    new_name = 'Lazada Store'
            if new_name and new_name != p.shop_name:
                p.shop_name = new_name[:150]
                updated += 1
        if updated:
            db.session.commit()
        return jsonify({'message': 'Backfill completed', 'updated': updated}), 200
    except Exception as e:
        db.session.rollback()
@main_bp.route('/api/products/backfill_classify', methods=['POST'])
def backfill_classify():
    """
    Find products that are Uncategorized or missing labels and re-classify them using their names.
    """
    try:
        updated = 0
        # Find products with 'Uncategorized' label or null category
        products = Product.query.filter(
            (Product.category_label == None) | 
            (Product.category_label == 'Uncategorized') |
            (Product.category_label == 'Other')
        ).all()

        for p in products:
            it_name, cat_name = infer_canonical_category_by_name(p.name)
            
            # Map/Sync with relational models
            item_type = get_or_create(ItemType, name=it_name)
            category = get_or_create(Category, name=cat_name, defaults={'item_type': item_type})
            
            p.item_type = item_type
            p.category = category
            p.category_label = it_name[:50]
            p.sub_category_label = cat_name[:50]
            
            # Re-finalize gender if it was unknown
            p.gender = _finalize_gender(p.gender or 'Unisex', it_name, cat_name, p.name)
            
            updated += 1

        if updated:
            db.session.commit()
        return jsonify({'message': 'Classification backfill completed', 'updated': updated}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Backfill error: {str(e)}'}), 500

@main_bp.route('/api/recolor', methods=['POST'])
def api_recolor():
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'image required'}), 400
        img_b = request.files['image'].read()
        color = request.form.get('color') or request.args.get('color') or '#ff0000'
        strength = float(request.form.get('strength') or request.args.get('strength') or 0.8)
        out_b, mime = recolor_clothing(img_b, color, strength)
        return Response(out_b, mimetype=mime)
    except Exception as e:
        return jsonify({'message': f'recolor error: {str(e)}'}), 500

@main_bp.route('/api/change-bg', methods=['POST'])
def api_change_bg():
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'image required'}), 400
        img_b = request.files['image'].read()
        blur = float(request.form.get('blur') or request.args.get('blur') or 0.0)
        bg_b = None
        if 'bg_image' in request.files:
            bg_b = request.files['bg_image'].read()
        bg_color = request.form.get('bg_color') or request.args.get('bg_color') or '#ffffff'
        out_b, mime = change_background(img_b, bg_color, bg_b, blur)
        return Response(out_b, mimetype=mime)
    except Exception as e:
        return jsonify({'message': f'change_bg error: {str(e)}'}), 500

@main_bp.route('/api/upscale', methods=['POST'])
def api_upscale():
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'image required'}), 400
        img_b = request.files['image'].read()
        scale = int(request.form.get('scale') or request.args.get('scale') or 2)
        out_b, mime = upscale_image(img_b, scale)
        return Response(out_b, mimetype=mime)
    except Exception as e:
        return jsonify({'message': f'upscale error: {str(e)}'}), 500

@main_bp.route('/api/shops', methods=['GET'])
def list_shops():
    """
    Aggregate distinct shops from Product table and derive shop URLs when possible.
    For Shopee product_url like /product/<shopid>/<itemid> → https://shopee.vn/shop/<shopid>
    For Lazada, fallback to homepage.
    """
    try:
        import re
        # Use all products (or last 500) to discover shops quickly
        products = Product.query.order_by(Product.id.desc()).limit(500).all()
        shops = {}
        for p in products:
            name = (p.shop_name or '').strip() or 'Unknown Shop'
            url = p.product_url or ''
            shop_url = None
            if 'shopee.vn' in url:
                m = re.search(r'/product/(\d+)/\d+', url)
                if m:
                    shop_id = m.group(1)
                    shop_url = f"https://shopee.vn/shop/{shop_id}"
            elif 'lazada.vn' in url:
                shop_url = "https://www.lazada.vn/"
            if name not in shops:
                shops[name] = {'shop_name': name, 'shop_url': shop_url, 'count': 0}
            # Prefer a discovered URL
            if not shops[name]['shop_url'] and shop_url:
                shops[name]['shop_url'] = shop_url
            shops[name]['count'] += 1
        # Overlay registry (saved by admin when crawl/save)
        try:
            registry_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'shops.json'))
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    saved_map = _json.load(f)
                    for n, v in saved_map.items():
                        if n not in shops:
                            shops[n] = {'shop_name': n, 'shop_url': v.get('shop_url'), 'count': 0}
                        else:
                            if v.get('shop_url'):
                                shops[n]['shop_url'] = v.get('shop_url')
        except Exception as _e:
            current_app.logger.warning(f"Shop registry read failed: {_e}")

        items = sorted(shops.values(), key=lambda x: x['shop_name'].lower())
        return jsonify(items), 200
    except Exception as e:
        return jsonify({'message': f'list_shops error: {str(e)}'}), 500

@main_bp.route('/api/admin/shops/rename', methods=['POST'])
def rename_shop():
    try:
        data = request.json or {}
        old = (data.get('old_name') or '').strip()
        new = (data.get('new_name') or '').strip()
        if not old or not new:
            return jsonify({'message': 'old_name and new_name required'}), 400
        if old == new:
            return jsonify({'message': 'No change'}), 200
        updated = Product.query.filter(Product.shop_name == old).update({'shop_name': new}, synchronize_session=False)
        db.session.commit()
        return jsonify({'message': 'ok', 'updated': updated}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'shop rename error: {str(e)}'}), 500

@main_bp.route('/api/products/<int:id>', methods=['GET', 'DELETE', 'PUT'])
def product_detail(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'message': 'Product not found'}), 404

    if request.method == 'GET':
        it_name = product.item_type.name if product.item_type else product.category_label
        cat_name = product.category.name if product.category else product.sub_category_label
        gender_disp = _finalize_gender(product.gender or 'Unisex', it_name, cat_name, product.name)
        return jsonify({
            'id': product.id,
            'item_id': product.item_id,
            'name': product.name,
            'image': product.image_url,
            'price': product.price,
            'category': product.item_type.name if product.item_type else product.category_label,
            'sub_category': product.category.name if product.category else product.sub_category_label,
            'style': product.style_ref.name if product.style_ref else product.style_label,
            'shop_name': product.shop_name,
            'product_url': product.product_url,
            'color': product.color.name if product.color else product.color_label,
            'color_tone': product.color.tone if product.color else product.color_tone,
            'season': product.season_ref.name if product.season_ref else product.season_label,
            'occasion': product.occasion_ref.name if product.occasion_ref else product.occasion_label,
            'gender': gender_disp,
            'material': product.material,
            'fit_type': product.fit_type,
            'details': product.details,
        }), 200

    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200

    if request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({'message': 'No changes provided'}), 400

        if 'name' in data:
            product.name = data['name']
        if 'price' in data:
            product.price = _parse_vnd_price(data['price'])
        if 'image' in data:
            product.image_url = data['image']
        if 'product_url' in data:
            product.product_url = data['product_url']
        elif 'shopee_link' in data:
            product.product_url = data['shopee_link']
        if 'shop_name' in data:
            product.shop_name = data['shop_name']
        if 'gender' in data:
            product.gender = data['gender']
        if 'material' in data:
            product.material = data['material']
        if 'fit_type' in data:
            product.fit_type = data['fit_type']
        if 'details' in data:
            product.details = data['details']

        category_field = data.get('category')
        sub_category_name = data.get('sub_category')

        if category_field or sub_category_name:
            if category_field and isinstance(category_field, str) and '|' in category_field:
                item_type_name, sub_category_name = [part.strip() for part in category_field.split('|', 1)]
            else:
                item_type_name = str(category_field).strip() if category_field else (product.item_type.name if product.item_type else product.category_label or 'Other')
                sub_category_name = sub_category_name or product.category.name if product.category else product.sub_category_label or 'Other'

            item_type = get_or_create(ItemType, name=item_type_name)
            category = get_or_create(Category, name=sub_category_name, defaults={'item_type': item_type})
            product.item_type = item_type
            product.category = category
            product.category_label = item_type_name[:50]
            product.sub_category_label = sub_category_name[:50]

        if 'style' in data:
            style_name = data['style'] or 'Casual'
            style = get_or_create(Style, name=style_name)
            product.style_ref = style
            product.style_label = style_name[:50]

        if 'color' in data or 'color_tone' in data:
            color_name = data.get('color', product.color.name if product.color else product.color_label or 'Multicolor')
            color_tone = data.get('color_tone', product.color.tone if product.color else product.color_tone or 'Pattern')
            color = get_or_create(Color, name=color_name, defaults={'tone': color_tone})
            if color.tone != color_tone and color_tone:
                color.tone = color_tone
            product.color = color
            product.color_label = color_name[:50]
            product.color_tone = color_tone[:20]

        if 'season' in data:
            season_name = data['season'] or 'All-season'
            season = get_or_create(Season, name=season_name)
            product.season_ref = season
            product.season_label = season_name[:50]

        if 'occasion' in data:
            occasion_name = data['occasion'] or 'Daily wear'
            occasion = get_or_create(Occasion, name=occasion_name)
            product.occasion_ref = occasion
            product.occasion_label = occasion_name[:50]

        db.session.commit()
        return jsonify({'message': 'Product updated successfully'}), 200


@main_bp.route('/api/dataset', methods=['GET'])
def export_dataset():
    export_format = (request.args.get('format') or 'json').lower()
    products = (
        Product.query
        .outerjoin(ItemType)
        .outerjoin(Category)
        .outerjoin(Color)
        .outerjoin(Style)
        .outerjoin(Season)
        .outerjoin(Occasion)
        .all()
    )

    dataset = []
    for p in products:
        dataset.append({
            'name': p.name,
            'item_type': p.item_type.name if p.item_type else p.category_label,
            'category': p.category.name if p.category else p.sub_category_label,
            'color': p.color.name if p.color else p.color_label,
            'color_tone': p.color.tone if p.color else p.color_tone,
            'style': p.style_ref.name if p.style_ref else p.style_label,
            'season': p.season_ref.name if p.season_ref else p.season_label,
            'occasion': p.occasion_ref.name if p.occasion_ref else p.occasion_label,
            'gender': p.gender,
            'material': p.material,
            'fit_type': p.fit_type,
            'price': p.price,
            'product_url': p.product_url,
        })

    if export_format == 'csv':
        output = io.StringIO()
        fieldnames = [
            'name',
            'item_type',
            'category',
            'color',
            'color_tone',
            'style',
            'season',
            'occasion',
            'gender',
            'material',
            'fit_type',
            'price',
            'product_url',
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dataset)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=fashion_dataset.csv'},
        )

    return jsonify({'count': len(dataset), 'items': dataset}), 200


@main_bp.route('/api/tryon', methods=['GET'])
def tryon():
    return jsonify({'status': 'success'}), 200

# --- Smart AI Coordination Routes ---

@main_bp.route('/api/ai/train', methods=['POST'])
def ai_train():
    """
    Triggers the heuristic 'training' process to analyze current inventory.
    """
    from .ai.coordinator import train_coordination_ai
    result = train_coordination_ai()
    return jsonify(result), 200

@main_bp.route('/api/ai/recommend', methods=['GET'])
def ai_recommend():
    """
    Get recommended items for a product ID.
    ?product_id=123
    """
    product_id = request.args.get('product_id')
    if not product_id:
        return jsonify({'message': 'product_id required'}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'message': 'Product not found'}), 404
        
    body_shape = request.args.get('body_shape')
    occasion = request.args.get('occasion')
        
    from .ai.coordinator import OutfitCoordinator
    rec_ids = OutfitCoordinator.get_recommendations(product, body_shape=body_shape, occasion=occasion)
    
    # Return full objects for frontend
    if not rec_ids:
         return jsonify({'target_id': int(product_id), 'recommendations': []}), 200

    recs = Product.query.filter(Product.id.in_(rec_ids)).all()
    payload = []
    for p in recs:
        payload.append({
            'id': p.id,
            'name': p.name,
            'image': p.image_url,
            'price': p.price,
            'style': p.style_ref.name if p.style_ref else p.style_label,
            'shop_name': p.shop_name
        })
        
    return jsonify({
        'target_id': int(product_id),
        'recommendations': payload
    }), 200
@main_bp.route('/api/ai/outfit-for-person', methods=['GET'])
def ai_outfit_for_person():
    """
    Generate an outfit for a specific body shape and occasion.
    ?body_shape=Hourglass&occasion=Tet&gender=Female
    """
    body_shape = request.args.get('body_shape', 'Rectangle')
    occasion = request.args.get('occasion', 'Play')
    gender = request.args.get('gender', 'Unisex')
    style = request.args.get('style')
    
    from .ai.coordinator import OutfitCoordinator
    ids = OutfitCoordinator.get_outfit_for_person(body_shape=body_shape, occasion=occasion, gender=gender, preferred_style=style, limit=4)
    
    if not ids:
        return jsonify({'recommendations': []}), 200
        
    recs = []
    # Fetch objects in correct order as returned by coordinator
    for rid in ids:
        p = Product.query.get(rid)
        if p:
            recs.append({
                'id': p.id,
                'name': p.name,
                'image': p.image_url,
                'price': p.price,
                'style': p.style_label or (p.style_ref.name if p.style_ref else 'Casual'),
                'shop_name': p.shop_name
            })
            
    return jsonify({
        'body_shape': body_shape,
        'occasion': occasion,
        'recommendations': recs
    }), 200
# ──────────────────────────────────────────────────────────────────────────────
# NEW ADMIN CRAWLER & CLASSIFIER ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@main_bp.route('/api/admin/crawl-shop', methods=['POST'])
def crawl_shopee_shop():
    data = request.get_json()
    shop_url = data.get('shop_url', '').strip()
    target_count = data.get('target_count', 40)
    skip_db = data.get('skip_db', False)

    if not shop_url:
        return jsonify({'success': False, 'error': 'Thieu shop_url'}), 400

    try:
        result = crawl_shopee_new(shop_url, target_count=target_count)
        if result['success'] and not skip_db:
            saved = save_products_to_db(result['products'])
            result['saved_to_db'] = saved
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/admin/classify-products', methods=['POST'])
def classify_products_route():
    data = request.get_json()
    shop_id = data.get('shop_id')

    # Lấy sản phẩm chưa classify từ DB
    import sqlite3 as sql
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
    
    conn = sql.connect(db_path)
    conn.row_factory = sql.Row
    cursor = conn.cursor()
    if shop_id:
        cursor.execute("SELECT * FROM products WHERE shop_id=? AND classification IS NULL", (shop_id,))
    else:
        cursor.execute("SELECT * FROM products WHERE classification IS NULL LIMIT 100")
    products = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not products:
        return jsonify({'message': 'Không có sản phẩm nào cần classify', 'classified': 0, 'saved': 0})

    try:
        classified = batch_classify(products, analyze_images=True)
        saved = save_classifications(classified)
        return jsonify({'success': True, 'classified': len(classified), 'saved': saved})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/admin/shop-profile/<shop_id>')
def get_shop_profile_route(shop_id):
    try:
        profile = build_shop_profile(shop_id)
        return jsonify(profile)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/admin/shop-mapping')
def get_shop_mapping_route():
    try:
        mapping = map_all_shops()
        return jsonify(mapping)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
