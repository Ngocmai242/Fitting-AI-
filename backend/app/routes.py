import csv
import io
import os
import time
import requests
import shutil
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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
from dotenv import load_dotenv

# Load HF_TOKEN from .env
load_dotenv()

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
import json as _json
from .ai.product_processor import process_garment_for_vton

import requests as _req, time as _time
import threading, queue
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# --- VTON Task Queue System ---
class VTONQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.results = {}
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        while True:
            task_id, func, args, kwargs = self.queue.get()
            try:
                # Basic cleanup of old results if dictionary grows too large
                if len(self.results) > 100:
                    try:
                        # Remove 20 oldest items
                        keys = list(self.results.keys())[:20]
                        for k in keys: self.results.pop(k, None)
                    except: pass

                print(f"[Queue] Processing task {task_id}...")
                result = func(*args, **kwargs)
                self.results[task_id] = {"status": "success", "data": result}
            except Exception as e:
                print(f"[Queue] Task {task_id} failed: {e}")
                self.results[task_id] = {"status": "error", "message": str(e)}
            finally:
                self.queue.task_done()

    def add_task(self, func, *args, **kwargs):
        task_id = str(uuid.uuid4())
        self.queue.put((task_id, func, args, kwargs))
        return task_id

    def get_result(self, task_id, timeout=120):
        start_time = _time.time()
        while _time.time() - start_time < timeout:
            if task_id in self.results:
                return self.results.pop(task_id)
            _time.sleep(1)
        return {"status": "error", "message": "Task timed out in queue"}

# Global queue instance
vton_processor_queue = VTONQueue()

# AI Imports
try:
    from .ai.pose import extract_keypoints
    from .ai.image_tools import remove_background_rgba, detect_clothing_color, recolor_clothing, upscale_image, change_background
    from .ai.features import compute_ratios, estimate_gender, predict_shape_with_confidence
    predict_shape = lambda *a, **kw: predict_shape_with_confidence(*a, **kw)[0]
except ImportError as e:
    print(f"[AI] Module import failed: {e}")
    # Fallback to dummies if imports fail
    def extract_keypoints(*args, **kwargs): return [], None
    def compute_ratios(*args, **kwargs): return {}
    def estimate_gender(*args, **kwargs): return "Unisex"
    def predict_shape(*args, **kwargs): return "Rectangle"
    def predict_shape_with_confidence(*args, **kwargs): return "Rectangle", 0.5
    def remove_background_rgba(*args, **kwargs): return None, None
    def recolor_clothing(*args, **kwargs): return None, None
    def upscale_image(*args, **kwargs): return None, None
    def change_background(*args, **kwargs): return None, None
    def detect_clothing_color(*args, **kwargs): return "Multicolor", "Pattern"

def map_category_to_fashn(db_category: str) -> str:
    """
    Chuyển đổi category trong DB sang format FASHN VTON 1.5.
    FASHN chỉ nhận: "tops" | "bottoms" | "one-pieces"
    """
    if not db_category:
        return "tops"  # mặc định

    cat = str(db_category).lower().strip()

    # BOTTOMS
    if cat.startswith("bottoms") or any(x in cat for x in [
        "quần", "jean", "jeans", "pants", "trousers", "shorts", "skirt", "legging"
    ]):
        return "bottoms"

    # ONE-PIECES (đầm, váy liền, jumpsuit)
    if any(x in cat for x in [
        "dress", "one-piece", "jumpsuit", "romper", "đầm", "váy liền", "vay", "dam"
    ]):
        return "one-pieces"

    # TOPS (mặc định cho tất cả áo)
    return "tops"

def map_garment_type_to_fashn(garment_type: str) -> str:
    """
    Chuyển garment_type từ frontend sang FASHN category.
    garment_type từ frontend: "tops" | "bottoms" | "dress" | "any"
    """
    mapping = {
        "tops":    "tops",
        "bottoms": "bottoms",
        "dress":   "one-pieces",
        "any":     "tops",  # default nếu không chọn
    }
    return mapping.get(str(garment_type).lower(), "tops")

def _wake_space(space_id):
    try:
        # Pinging the space UI usually wakes it up if it's sleeping
        _req.get(f"https://huggingface.co/spaces/{space_id}", timeout=8)
        _time.sleep(4)
    except Exception:
        pass

def _make_fallback(person_img_path):
    """Tạo ảnh fallback: ảnh gốc + banner vàng ở dưới"""
    out_name = f"fallback_{uuid.uuid4().hex}.jpg"
    results_dir = os.path.join(current_app.static_folder, 'static', 'tryon_results')
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, out_name)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(person_img_path).convert("RGB")
        w, h = img.size
        draw = ImageDraw.Draw(img)
        # Use a default font
        try:
            # Typical Windows font paths or fallback to default
            font = None
            for font_path in ["arial.ttf", "C:\\Windows\\Fonts\\arial.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
                try:
                    font = ImageFont.truetype(font_path, 20)
                    break
                except: continue
            if not font: font = ImageFont.load_default()
        except IOError:
            font = ImageFont.load_default()
            
        draw.rectangle([0, h - 44, w, h], fill=(255, 193, 7))
        draw.text(
            (10, h - 32),
            "⚠  AI is busy — please try again later. Outfits below are still recommended!",
            fill=(0, 0, 0),
            font=font
        )
        img.save(out_path, "JPEG", quality=92)
    except Exception:
        shutil.copy(person_img_path, out_path)
    return out_path

def is_busy_error(exception):
    """Checks if the exception is due to server busy/overloaded."""
    err_msg = str(exception).lower()
    if "busy" in err_msg or "queue" in err_msg or "overloaded" in err_msg:
        return True
    # HTTP errors if applicable
    if hasattr(exception, 'status_code') and exception.status_code in [429, 503]:
        return True
    return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(is_busy_error),
    reraise=True # Important to let the caller handle it if all retries fail
)
def call_fashn_vton_raw(person_path, garment_path, fashn_cat, space_id, hf_token):
    from gradio_client import Client, handle_file
    print(f"[FASHN-VTON] Connecting to {space_id}...")
    _wake_space(space_id)
    client = Client(space_id, hf_token=hf_token) if hf_token else Client(space_id)
    
    # fashn-vton-1.5 signature: person_image, garment_image, category
    # Some mirrors might use api_name='/run' or '/predict'
    try:
        result = client.predict(
            person_image=handle_file(person_path),
            garment_image=handle_file(garment_path),
            category=fashn_cat,
        )
    except Exception as e:
        print(f"[FASHN-VTON] Keyword 'person_image' failed, trying 'model_image'...")
        # Fallback to model_image if person_image fails (some mirrors use it)
        result = client.predict(
            model_image=handle_file(person_path),
            garment_image=handle_file(garment_path),
            category=fashn_cat,
        )
    return result

def call_fashn_vton(person_path, garment_path, category="tops"):
    """
    Calls FASHN VTON v1.5 on Hugging Face (FREE 100%).
    category in ["tops", "bottoms", "one-pieces"]
    """
    try:
        from gradio_client import Client, handle_file
    except ImportError:
        print("[FASHN-VTON] gradio_client missing")
        return person_path, True

    # Use the official FASHN VTON space or a reliable mirror
    space_id = "fashn-ai/fashn-vton-1.5"
    hf_token = os.getenv("HF_TOKEN", "")
    
    # Normalize category for FASHN
    cat_map = {
        "tops": "tops", "top": "tops", "shirt": "tops", "ao": "tops",
        "bottoms": "bottoms", "bottom": "bottoms", "pants": "bottoms", "quan": "bottoms",
        "one-pieces": "one-pieces", "dress": "one-pieces", "vay": "one-pieces"
    }
    fashn_cat = cat_map.get(str(category).lower(), "tops")

    try:
        # Use the raw caller with retry
        result = call_fashn_vton_raw(person_path, garment_path, fashn_cat, space_id, hf_token)
        
        # Result processing
        result_raw = result[0] if isinstance(result, (list, tuple)) else result
        if isinstance(result_raw, dict):
            result_raw = result_raw.get("path") or result_raw.get("url") or str(result_raw)

        results_dir = os.path.join(current_app.static_folder, "static", "tryon_results")
        os.makedirs(results_dir, exist_ok=True)
        out_name = f"fashn_{uuid.uuid4().hex}.png"
        out_path = os.path.join(results_dir, out_name)
        shutil.copy(str(result_raw), out_path)
        
        print(f"[FASHN-VTON] SUCCESS -> {out_path}")
        return out_path, False
    except Exception as e:
        print(f"[FASHN-VTON] FAIL after retries: {e}")
        return person_path, True

    except Exception:
        return 0.0

def _get_image_similarity(path1, path2):
    """Simple check if two images are the same (pixel-wise or hash)"""
    try:
        from PIL import Image
        import numpy as np
        img1 = Image.open(path1).convert("L").resize((64, 64))
        img2 = Image.open(path2).convert("L").resize((64, 64))
        arr1 = np.array(img1).astype(float) / 255.0
        arr2 = np.array(img2).astype(float) / 255.0
        # Mean absolute difference
        diff = np.mean(np.abs(arr1 - arr2))
        # If diff < 0.05, they are > 95% similar
        return 1.0 - diff
    except Exception:
        return 0.0

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception(is_busy_error),
    reraise=True
)
def call_idm_vton_raw(client, person_path, garment_path, api_name=None):
    from gradio_client import handle_file
    if api_name:
        return client.predict(
            dict={"background": handle_file(person_path), "layers": [], "composite": None},
            garm_img=handle_file(garment_path),
            garment_des="",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name=api_name,
        )
    else:
        return client.predict(
            dict={"background": handle_file(person_path), "layers": [], "composite": None},
            garm_img=handle_file(garment_path),
            garment_des="",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
        )

def call_idm_vton(person_path, garment_path):
    """
    Calls IDM-VTON on Hugging Face Space to perform virtual try-on.
    Returns (local_path, is_fallback).
    """
    try:
        from gradio_client import Client, handle_file
    except ImportError:
        print("[IDM-VTON] gradio_client not installed -> fallback")
        return _make_fallback(person_path), True

    spaces = [
        "yisol/IDM-VTON",
        "freddyaboulton/IDM-VTON",
        "adi1516/IDM_VTON",
    ]

    hf_token = os.getenv("HF_TOKEN", "")
    results_dir = os.path.join(current_app.static_folder, "static", "tryon_results")
    os.makedirs(results_dir, exist_ok=True)

    # Try common api names; spaces sometimes change endpoints.
    api_names = ["/tryon", "/run/predict", None]

    for space_id in spaces:
        for api_name in api_names:
            try:
                print(f"[IDM-VTON] Trying {space_id} (api_name={api_name})...")
                _wake_space(space_id)

                # gradio_client expects `hf_token` (older code used `token`)
                client = Client(space_id, hf_token=hf_token) if hf_token else Client(space_id)

                result = call_idm_vton_raw(client, person_path, garment_path, api_name=api_name)

                result_raw = result[0] if isinstance(result, (list, tuple)) else result
                if isinstance(result_raw, dict):
                    result_raw = (
                        result_raw.get("url")
                        or result_raw.get("path")
                        or result_raw.get("value")
                        or str(result_raw)
                    )

                ext = os.path.splitext(str(result_raw))[1] or ".jpg"
                out_name = f"result_{uuid.uuid4().hex}{ext}"
                out_path = os.path.join(results_dir, out_name)
                shutil.copy(str(result_raw), out_path)

                print(f"[IDM-VTON] SUCCESS {space_id} -> {out_path}")
                return out_path, False

            except Exception as e:
                print(f"[IDM-VTON] FAIL {space_id} (api_name={api_name}): {type(e).__name__}: {str(e)[:200]}")
                time.sleep(2)
                continue

    print("[IDM-VTON] All spaces failed -> fallback")
    return _make_fallback(person_path), True

def download_garment_image(image_url: str, shopee_url: str):
    """
    Download ảnh garment về local. Thử image_url trước, nếu lỗi thử shopee_url.
    Trả về đường dẫn file local, hoặc None nếu hoàn toàn thất bại.
    """
    save_dir = os.path.join(current_app.static_folder, 'uploads', 'tryon')
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    os.makedirs(save_dir, exist_ok=True)

    urls_to_try = []
    if image_url and image_url.startswith("http"):
        urls_to_try.append(image_url)
    if shopee_url and shopee_url.startswith("http"):
        # Shopee thường có ảnh thumbnail trong URL
        urls_to_try.append(shopee_url)

    for url in urls_to_try:
        try:
            resp = _req.get(url, timeout=12, headers=headers, allow_redirects=True)
            ct   = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and len(resp.content) > 5000 and "image" in ct:
                # Xác định extension
                ext = ".jpg"
                if "png" in ct:  ext = ".png"
                if "webp" in ct: ext = ".webp"
                filename = f"garment_{uuid.uuid4().hex}{ext}"
                path = os.path.join(save_dir, filename)
                
                content_to_save = resp.content
                
                # Check if image has a person (requires cleaning)
                try:
                    people, err = extract_keypoints(resp.content)
                    if not err and len(people) > 0:
                        print(f"[Garment] Person detected in garment image. Cleaning...")
                        clean_bytes, _ = remove_background_rgba(resp.content)
                        if clean_bytes:
                            content_to_save = clean_bytes
                            # Update extension to .png for clean image
                            ext = ".png"
                            filename = f"garment_clean_{uuid.uuid4().hex}{ext}"
                            path = os.path.join(save_dir, filename)
                except Exception as ce:
                    print(f"[Garment] Cleaning failed: {ce}")

                with open(path, "wb") as f:
                    f.write(content_to_save)
                
                print(f"[Garment] Saved: {len(content_to_save)//1024}KB -> {path}")
                return path
            else:
                print(f"[Garment] Bad response: HTTP={resp.status_code} | size={len(resp.content)} | {url[:60]}")
        except Exception as e:
            print(f"[Garment] Failed: {type(e).__name__}: {str(e)[:80]} | {url[:60]}")
            continue

    print("[Garment] All URLs failed -> cannot get garment image")
    return None

def _is_allowed_image_file(file_storage) -> bool:
    try:
        ct = (file_storage.content_type or "").lower()
        if ct in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
            return True
        fn = (file_storage.filename or "").lower()
        return fn.endswith((".jpg", ".jpeg", ".png", ".webp"))
    except Exception:
        return False

def _clean_image_with_yolo(input_path, item_id, target_model='product'):
    """
    Tự động xử lý ảnh sản phẩm dùng YOLO + Rembg (Step 1).
    Trả về đường dẫn tương đối (với /static) để lưu vào DB.
    """
    try:
        from .ai.product_processor import extract_main_product
        
        # Đảm bảo đường dẫn input là tuyệt đối
        if not os.path.isabs(input_path):
            input_path = os.path.abspath(os.path.join(current_app.static_folder, input_path.lstrip("/")))

        # Thư mục lưu kết quả
        processed_dir = os.path.join(current_app.static_folder, 'uploads', 'cleaned')
        os.makedirs(processed_dir, exist_ok=True)
        
        # Tên file kết quả
        out_name = f"clean_{item_id}_{uuid.uuid4().hex[:8]}.png"
        out_path = os.path.join(processed_dir, out_name)
        
        print(f"[Cleaner] YOLO Processing: {input_path} -> {out_path}")
        result_path = extract_main_product(input_path, out_path)
        
        if result_path and os.path.exists(result_path):
            # Trả về đường dẫn tương đối từ static folder (ví dụ: /uploads/cleaned/...)
            return f"/uploads/cleaned/{out_name}"
    except Exception as e:
        print(f"[Cleaner] YOLO processing failed: {e}")
    return None

def _resolve_clean_abs(clean_rel):
    """Resolve relative clean_image_path to absolute filesystem path."""
    if not clean_rel: return None
    try:
        rel = str(clean_rel).lstrip("/").replace("\\", "/")
        # Try both with and without 'static' prefix
        if not rel.startswith("static"):
             abs_path = os.path.abspath(os.path.join(current_app.static_folder, rel))
        else:
             rel_clean = rel.replace("static/", "", 1)
             abs_path = os.path.abspath(os.path.join(current_app.static_folder, rel_clean))
             
        if os.path.exists(abs_path):
            return abs_path
    except Exception:
        pass
    return None

def ai_virtual_tryon(
    photo_path: str,
    gender: str,
    occasion: str,
    style: str,
    body_shape: str,
    result_path: str,
) -> str:
    """
    Placeholder Virtual Try-On. If/when ai_engine exists, integrate here.
    Current behavior: copies original image to result_path (never crashes the flow).
    """
    try:
        os.makedirs(os.path.dirname(result_path), exist_ok=True)
        shutil.copyfile(photo_path, result_path)
        return result_path
    except Exception:
        try:
            shutil.copyfile(photo_path, result_path)
            return result_path
        except Exception:
            return photo_path

def _get_demo_products():
    return [
        {
            "id": 1,
            "name": "Áo Sơ Mi Trắng Korean",
            "price": 185000,
            "image_url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=400&q=80",
            "shopee_url": "https://shopee.vn/search?keyword=ao+so+mi+trang+korean"
        },
        {
            "id": 2,
            "name": "Quần Baggy Beige",
            "price": 249000,
            "image_url": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400&q=80",
            "shopee_url": "https://shopee.vn/search?keyword=quan+baggy+beige"
        },
        {
            "id": 3,
            "name": "Đầm Midi Floral",
            "price": 320000,
            "image_url": "https://images.unsplash.com/photo-1612722432474-b971cdcea546?w=400&q=80",
            "shopee_url": "https://shopee.vn/search?keyword=dam+midi+floral"
        },
        {
            "id": 4,
            "name": "Set Crop Top + Chân Váy",
            "price": 275000,
            "image_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&q=80",
            "shopee_url": "https://shopee.vn/search?keyword=set+crop+top+chan+vay"
        },
        {
            "id": 5,
            "name": "Áo Thun Basic Tee",
            "price": 120000,
            "image_url": "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&q=80",
            "shopee_url": "https://shopee.vn/search?keyword=ao+thun+basic"
        },
        {
            "id": 6,
            "name": "Áo Khoác Denim",
            "price": 380000,
            "image_url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=400&q=80",
            "shopee_url": "https://shopee.vn/search?keyword=ao+khoac+denim"
        },
    ]

def get_recommended_outfits(gender, occasion, style, body_shape, budget, garment_type="any", limit=6):
    """
    Fetch products from database based on filters.
    """
    try:
        query = Product.query
        
        # Gender filter
        if gender and gender.lower() != 'unisex':
             # Match specific gender or unisex items
             query = query.filter((Product.gender == gender) | (Product.gender == 'unisex'))
        
        # Occasion filter
        if occasion and occasion.lower() != 'any':
             query = query.filter(Product.occasion == occasion)
             
        # Style filter
        if style and style.lower() != 'any':
             query = query.filter((Product.style_tag == style) | (Product.style_label == style))

        def _garment_synonyms(gt: str) -> list[str]:
            gt = (gt or "").lower().strip()
            if not gt or gt == "any":
                return []
            if gt in ("dress", "dresses", "đầm", "váy"):
                return ["dress", "skirt", "vay", "dam", "chan vay"]
            if gt in ("tops", "top", "áo"):
                return ["tops", "top", "ao", "shirt", "tee", "tshirt", "blouse", "hoodie", "sweater"]
            if gt in ("bottoms", "bottom", "quần"):
                return ["bottoms", "bottom", "quan", "skirt", "jeans", "pants", "short"]
            return [gt]

        # Garment type filter - IMPROVED
        if garment_type and str(garment_type).lower() != "any":
            gt = str(garment_type).lower()
            syns = _garment_synonyms(gt)
            
            from sqlalchemy import or_
            ors = []
            
            if gt == "full outfit":
                ors.extend([
                    Product.category_label.ilike("top%"),
                    Product.category_label.ilike("bottom%"),
                    Product.sub_category_label.ilike("ao%"),
                    Product.sub_category_label.ilike("quan%")
                ])
            else:
                # Rule 2: Accurate Category mapping for dress/skirt
                for s in syns:
                    ors.append(Product.category_label.ilike(f"%{s}%"))
                    ors.append(Product.sub_category_label.ilike(f"%{s}%"))
                    ors.append(Product.name.ilike(f"%{s}%"))
            
            if ors:
                query = query.filter(or_(*ors))
             
        # Budget filter
        if budget and budget.lower() != 'any':
             if budget == 'under200':
                  query = query.filter(Product.price < 200000)
             elif budget == '200-500':
                  query = query.filter(Product.price >= 200000, Product.price <= 500000)
             elif budget == '500-1000':
                  query = query.filter(Product.price >= 500000, Product.price <= 1000000)
             elif budget == 'above1000':
                  query = query.filter(Product.price > 1000000)
        
        # Order by random and limit
        from sqlalchemy import func
        products = query.order_by(func.random()).limit(limit).all()
        
        if not products:
             # Fallback: get any products if filter is too strict (never return empty)
             products = Product.query.order_by(func.random()).limit(limit).all()
             if not products:
                  return _get_demo_products()

        results = []
        for p in products:
            it_name = p.item_type.name if getattr(p, "item_type", None) else (p.category_label or "")
            cat_name = p.category.name if getattr(p, "category", None) else (p.sub_category_label or "")
            garment = getattr(p, "garment_type", None) if hasattr(p, "garment_type") else None
            if not garment:
                it_low = str(it_name or "").lower()
                cat_low = str(cat_name or "").lower()
                if it_low in ("tops", "bottoms") and cat_low:
                    garment = f"{it_low} ({cat_low})"
                elif it_low:
                    garment = it_low
            results.append({
                'id': p.id,
                'name': p.name,
                'price': p.price,
                'image_url': p.image_url,
                'clean_image_path': getattr(p, "clean_image_path", None),
                'shopee_url': getattr(p, "shopee_url", None) or p.product_url or f"https://shopee.vn/search?keyword={p.name}",
                'garment_type': garment,
                'gender': (p.gender or "unisex").lower()
            })
        return results
    except Exception as e:
        print(f"[DB] Recommend error: {e}")
        return _get_demo_products()

# Removed dummy AI functions - now imported from .ai package

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
    from data_engine.shopee_crawler import crawl_shopee_new, save_products_to_db
    from data_engine.product_classifier import batch_classify, save_classifications, build_shop_profile, map_all_shops
    from data_engine.image_cleaner import batch_clean_from_db
    from data_engine.product_tagger import tag_all_products
except ImportError as e:
    print(f"Could not import new crawlers/classifiers: {e}")
    # Fallbacks to prevent NameError
    def crawl_shopee_new(*args, **kwargs):
        return {"success": False, "error": f"Crawler not available: {e}", "products": []}
    def save_products_to_db(*args, **kwargs): return 0
    def batch_classify(*args, **kwargs): return []
    def save_classifications(*args, **kwargs): return 0
    def build_shop_profile(*args, **kwargs): return {}
    def map_all_shops(*args, **kwargs): return {}

try:
    from data_engine.crawler.shopee import crawl_shop_url as crawl_shopee
except ImportError as e:
    print(f"Could not import shopee crawler: {e}")
    def crawl_shopee(url, limit=50): return []

try:
    from data_engine.crawler.lazada import crawl_lazada_shop_url as crawl_lazada
except ImportError as e:
    # Lazada is optional
    def crawl_lazada(url, limit=50): return []

CRAWLER_AVAILABLE = True # Always True now since we use requests


main_bp = Blueprint('main', __name__)

# --- Auth utility ---
@main_bp.route('/api/logout', methods=['POST'])
def logout_api():
    """Clear server-side session."""
    try:
        session.clear()
    except Exception:
        pass
    return jsonify({'success': True}), 200

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
    if any(k in n for k in ["chan vay", "skirt", "vay"]):
        return "dresses_skirts", "skirt"
    if any(k in n for k in ["dam ", " dress", "vay lien"]):
        return "dresses_skirts", "dress"
    if any(k in n for k in ["jean", "denim"]):
        return "bottoms", "jeans"
    if any(k in n for k in ["quan tay", "trouser", "quan au", "quan dai", "quan baggy", "quan ong suong", "quan jogger"]):
        return "bottoms", "trousers"
    if any(k in n for k in ["short", "quan dui", "shorts"]):
        return "bottoms", "shorts"
    if "quan" in n:
        return "bottoms", "trousers"

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
    
    # Default safe
    return "tops", "t_shirt"

def validate_and_fix_category(name: str, category: str, sub_category: str = "") -> tuple[str, str]:
    """
    Enforces category consistency. If 'quần' is in the name, it must be bottoms.
    """
    n = _norm_ascii(name)
    c = str(category or "").lower()
    
    # Bottoms enforcement
    BOTTOMS_KEYWORDS = ["quan", "jean", "denim", "trouser", "short", "skirt", "chan vay"]
    if any(k in n for k in BOTTOMS_KEYWORDS):
        if not c.startswith("bottoms") and "dresses_skirts" not in c:
            return infer_canonical_category_by_name(name)
            
    # Dress enforcement
    DRESS_KEYWORDS = ["dam", "vay lien", "jumpsuit"]
    if any(k in n for k in DRESS_KEYWORDS):
        if c != "dresses_skirts" and c != "one-piece":
            return infer_canonical_category_by_name(name)
            
    return category, sub_category

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
def _finalize_gender(initial, item_type_name, category_name, product_name):
    g = (initial or "Unisex").strip()
    cat = _norm_ascii(category_name or "")
    name_norm = _norm_ascii(product_name or "")
    name_padded = " " + name_norm + " "

    # --- Unisex keywords (explicit) ---
    unisex_phrases = [
        "nam nu",
        "nu nam",
        "unisex",
        "nam va nu",
        "couple",
        "ca nam ca nu",
    ]
    if any(p in name_norm for p in unisex_phrases):
        return "Unisex"

    # --- Male tokens: ưu tiên và match theo từ độc lập ---
    male_explicit = ["nam", "men", "male", "boy", "gentleman", "quan nam", "ao nam", "cho nam"]
    is_male = any(
        (" " + tok + " ") in name_padded
        or name_padded.startswith(tok + " ")
        or name_padded.endswith(" " + tok)
        for tok in male_explicit
    )

    # --- Female categories ---
    female_cats = {
        "crop_top",
        "dress",
        "skirt",
        "blouse",
        "camisole",
        "tube_top",
        "off_shoulder",
        "bralette",
        "babydoll",
        "peplum",
        "vay nu",
        "dam nu",
        "chan vay",
    }

    # --- Female substrings trong category (đã loại bỏ token quá ngắn gây false positive) ---
    female_cat_substrings = [
        "crop",
        "dress",
        "skirt",
        "blouse",
        "camisole",
        "tube",
        "off shoulder",
        "tre vai",
        "yem",
        "hai day",
        "bodycon",
        "babydoll",
        "peplum",
    ]

    # --- Female tokens trong tên (đã loại bỏ 'no' và các token dễ match nhầm) ---
    female_name_tokens = [
        "nu ",
        " nu",
        "women",
        "girl",
        "lady",
        "dam ",
        " dam",
        "vay ",
        " vay",
        "croptop",
        "crop top",
        "hai day",
        "2 day",
        "yem ",
        " yem",
        "skirt",
        "dress",
        "jumpsuit",
        "blouse",
        "camisole",
        "tube top",
        "off shoulder",
        "bralette",
        "babydoll",
        "peplum",
        "xinh xan",
        "de thuong nu",
        "nu tinh",
        "danh nu",
        "thoi trang nu",
        "chan vay",
    ]

    is_female_cat = cat.replace(" ", "_") in female_cats or any(sub in cat for sub in female_cat_substrings)
    is_female_name = any(tok in name_padded for tok in female_name_tokens)

    # --- Detecting Male signals in Category ---
    male_cat_substrings = ["nam", "men", "male", "boy"]
    is_male_cat = any(sub in cat for sub in male_cat_substrings)

    # --- Final Logic ---
    # 1. Nếu có signal nam rõ rệt trong category hoặc tên, và KHÔNG có category đặc thù nữ (váy, đầm...)
    if (is_male or is_male_cat) and not is_female_cat:
        return "Male"
    
    # 2. Nếu có signal nữ rõ rệt
    if is_female_cat or is_female_name:
        # Kiểm tra lại xem có phải unisex không (có cả nam và nữ)
        if is_male or is_male_cat:
            return "Unisex"
        return "Female"

    # 3. Mặc định theo initial hoặc Unisex
    if g.lower() == "unisex" or (not is_male and not is_female_name):
        return "Unisex"
        
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
    print(f"Username: {data.get('username')}")
    print(f"Email: {data.get('email')}")
    print(f"Phone: {data.get('phone')}")
    
    # Clean input
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip() if data.get('phone') else ''
    password = data.get('password', '').strip()
    
    # Check if user already exists
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        print(f"ERROR: User already exists - {existing_user.username}")
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
        
        print(f"[AUTH] USER CREATED SUCCESSFULLY:")
        print(f"   - ID: {new_user.id}")
        print(f"   - Username: {new_user.username}")
        print(f"   - Role: {new_user.role}")
        print(f"   - Status: {new_user.status}")
        print(f"=========================\n")
        
        return jsonify({'message': 'Registered successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] REGISTRATION ERROR: {str(e)}")
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
        
        # Step 1: Clean image for outfit
        if new_outfit.image_url:
            uid = uuid.uuid4().hex[:6]
            cleaned = _clean_image_with_yolo(new_outfit.image_url, f"outfit_{uid}")
            if cleaned:
                new_outfit.clean_image_path = cleaned

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
            # Sử dụng Playwright crawler v6 mới
            limit = data.get('limit', 40)
            result = crawl_shopee_new(shop_url, target_count=limit)
            
            if not result.get("success"):
                return jsonify({
                    'message': f'Lỗi Shopee: {result.get("error")}',
                    'products': [],
                    'count': 0
                }), 200
            
            crawled_products = result.get("products", [])
        
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

@main_bp.route('/api/admin/crawl/save-preview', methods=['POST'])
def save_crawled_products_preview():
    """Lưu sản phẩm Shopee/Lazada (flow cũ) vào ORM Product + taxonomy."""
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
            # BUG 3 Fix: Sử dụng đúng mapping item_id (composite string) từ crawler
            item_id_str = item.get('id') or item.get('variant_id') or item.get('itemid') or item.get('item_id')
            link_value = item.get('product_url') or item.get('shopee_link') or item.get('url')

            if not item_id_str and not link_value:
                continue

            # Query theo item_id (string unique) thay vì id (integer PK)
            product = Product.query.filter_by(item_id=str(item_id_str)).first()
            
            if not product and link_value:
                product = Product.query.filter_by(product_url=link_value[:2000]).first()

            created = False
            if not product:
                if not item_id_str:
                    continue
                product = Product(item_id=str(item_id_str))
                db.session.add(product)
                created = True
            
            # Gán Shopee item_id số (nếu có) vào biến shopee_id_num (chỉ dùng để lưu metadata)
            # Tuy nhiên trong DB hiện tại item_id là string, nên ta giữ nguyên item_id_str
            # Nếu models.py có thêm trường item_id_numeric thì mới cần parse int.
            # Ở đây ta cập nhật các field khác.

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
            if vn_cat in ('', 'other', 'khac', 'khác', 'phan loai khac', 'phân loại khác'):
                item_type_name, category_name = 'tops', 't_shirt'

            # Final validation before saving
            item_type_name, category_name = validate_and_fix_category(product.name, item_type_name, category_name)

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
        print(f"Save Crawl Error: {e}")
        return jsonify({'message': f'Database error: {str(e)}'}), 500

# ──────────────────────────────────────────────────────────────────────────────
# AI Data Normalization Pipeline (Admin only)
# ──────────────────────────────────────────────────────────────────────────────
@main_bp.route('/api/admin/normalize-dataset', methods=['POST'])
def normalize_dataset_api():
    """
    Trigger the AI Preprocessing Pipeline:
    1. Download raw images
    2. Segment & Clean background
    3. Categorize correct VTON category (tops/bottoms/one-pieces)
    """
    try:
        import sqlite3
        limit = int(request.json.get('limit', 50))
        overwrite = bool(request.json.get('overwrite', False))
        product_ids = request.json.get('product_ids', []) # NEW: Nhận list ID
        
        from data_engine.image_cleaner import batch_clean_from_db, clean_product_image
        from data_engine.product_classifier import batch_classify, save_classifications
        
        db_path = os.path.abspath(os.path.join(current_app.root_path, '..', '..', 'database', 'database_v2.db'))
        
        print(f"[Admin] Starting Normalization Pipeline (IDS={len(product_ids)}, limit={limit})...")
        
        # Step 1 & 2: Clean Images
        cleaned_count = 0
        if product_ids:
            # Xử lý theo danh sách ID cụ thể
            from app.models import Product
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            SAVE_DIR = os.path.join(current_app.static_folder, "clean_images") # Lưu vào static cho frontend
            os.makedirs(SAVE_DIR, exist_ok=True)
            
            for pid in product_ids:
                p = db.session.get(Product, pid)
                if p and p.image_url:
                    clean_path = clean_product_image(p.image_url, p.item_id or p.id, SAVE_DIR)
                    if clean_path:
                        p.clean_image_path = clean_path
                        cleaned_count += 1
            db.session.commit()
        else:
            # Xử lý hàng loạt như cũ
            cleaned_count = batch_clean_from_db(db_path, limit=limit, overwrite=overwrite)
        
        # Step 3: Classify (Update categories)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        if product_ids:
            # Chỉ lấy các sản phẩm vừa chọn để classify
            ids_str = ",".join(map(str, product_ids))
            query = f"SELECT id, name, image_url as image FROM products WHERE id IN ({ids_str})"
        else:
            query = "SELECT id, name, image_url as image FROM products"
            if not overwrite:
                query += " WHERE classification IS NULL OR classification = ''"
            query += f" LIMIT {limit}"
        
        products_to_classify = [dict(r) for r in cur.execute(query).fetchall()]
        conn.close()
        
        if products_to_classify:
            print(f"[Admin] Classifying {len(products_to_classify)} products...")
            classified = batch_classify(products_to_classify, analyze_images=False)
            save_classifications(classified, db_path)
            
        return jsonify({
            'success': True,
            'message': f'Normalization completed: {cleaned_count} images cleaned, {len(products_to_classify)} products classified.',
            'cleaned_count': cleaned_count,
            'classified_count': len(products_to_classify)
        }), 200
        
    except Exception as e:
        print(f"[Admin] Normalization Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'GET':
        # Use joinedload to fetch normalization status in one query
        from sqlalchemy.orm import joinedload
        products = Product.query.options(joinedload(Product.normalized_entry)).order_by(Product.id.desc()).limit(150).all()
        payload = []
        for p in products:
            it_name = p.item_type.name if p.item_type else p.category_label
            cat_name = p.category.name if p.category else p.sub_category_label
            gender_disp = _finalize_gender(p.gender or 'Unisex', it_name, cat_name, p.name)
            
            # Trạng thái chuẩn hóa
            norm_status = 'raw'
            if p.clean_image_path:
                norm_status = 'clean'
            elif p.normalized_entry:
                norm_status = p.normalized_entry.status # 'pending' | 'processing' | 'failed'

            payload.append({
                'id': p.id,
                'item_id': p.item_id,
                'name': p.name,
                'image': p.image_url,
                'clean_image_path': p.clean_image_path,
                'norm_status': norm_status,
                'price': p.price,
                'category': it_name,
                'sub_category': cat_name,
                'product_url': p.product_url,
                'shopee_url': getattr(p, "shopee_url", None) or p.product_url,
                'style_tag': getattr(p, "style_tag", None),
                'body_shape_tag': getattr(p, "body_shape_tag", None),
                'color': p.color.name if p.color else (p.color_primary or p.color_label),
                'color_primary': p.color_primary,
                'color_secondary': p.color_secondary,
                'hex_primary': p.hex_primary,
                'color_tone': p.color.tone if p.color else p.color_tone,
                'season': p.season_ref.name if p.season_ref else (p.season or p.season_label or 'All-season'),
                'occasion': p.occasion_ref.name if p.occasion_ref else (p.occasion or p.occasion_label or 'Daily wear'),
                'gender': gender_disp,
                'material': p.material,
                'style': p.style_ref.name if p.style_ref else p.style_label,
                'fit_type': p.fit_type,
                'details': p.details,
                'shop_name': p.shop_name,
                'clean_image_paths': _json.loads(p.clean_image_paths) if p.clean_image_paths else [],
                'has_model': p.has_model,
                'image_type': getattr(p, 'image_type', 'unknown')
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
        # Step 1: Clean image with YOLO + Rembg
        if product.image_url:
            cleaned = _clean_image_with_yolo(product.image_url, product.item_id)
            if cleaned:
                product.clean_image_path = cleaned
        incoming_url = (data.get('shopee_url') or data.get('product_url') or data.get('shopee_link') or '').strip()
        product.product_url = incoming_url[:2000]
        try:
            product.shopee_url = incoming_url[:2000]
        except Exception:
            pass
        product.price = _parse_vnd_price(data.get('price', 0))
        product.shop_name = (data.get('shop_name') or 'Manual Entry')[:150]
        # For manual entry, we default to valid=True as the user is inputting it
        product.is_valid = True

        _norm = normalize_product_fields(data)
        # Allow admin to explicitly set gender/occasion/style_tag/body_shape_tag for Try-On filters
        product.gender = (data.get("gender") or _norm["gender"] or "")[:20]
        product.material = _norm["material"][:100]
        product.fit_type = _norm["fit_type"][:50]
        product.color_tone = _norm["color_tone"][:20]
        product.details = _norm["details"]
        try:
            product.occasion = (data.get("occasion") or _norm.get("occasion_name") or product.occasion or "")[:50]
        except Exception:
            pass
        try:
            product.style_tag = (data.get("style_tag") or "")[:100] if data.get("style_tag") else (product.style_tag or None)
        except Exception:
            pass
        try:
            product.body_shape_tag = (data.get("body_shape_tag") or "")[:100] if data.get("body_shape_tag") else (product.body_shape_tag or None)
        except Exception:
            pass

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

        item_type_name, sub_category_name = validate_and_fix_category(product.name, item_type_name, sub_category_name)

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
    Combined shop history from both the Product database and the dedicated shops registry table.
    """
    try:
        import sqlite3
        import re
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
        
        shops = {}
        
        # 1. First, get shops from the dedicated 'shops' table (History)
        try:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shops'")
                if cursor.fetchone():
                    rows = cursor.execute("SELECT shop_id, display_name, shop_url, last_crawled FROM shops ORDER BY last_crawled DESC").fetchall()
                    for row in rows:
                        name = (row['display_name'] or '').strip()
                        if name:
                            shops[name] = {
                                'shop_name': name,
                                'shop_url': row['shop_url'],
                                'shop_id': row['shop_id'],
                                'count': 0,
                                'last_crawled': row['last_crawled']
                            }
                conn.close()
        except Exception as e:
            current_app.logger.warning(f"Error reading shops table: {e}")

        # 2. Extract from Product table (Actual stored items)
        products = Product.query.with_entities(Product.shop_name, Product.product_url, Product.id).order_by(Product.id.desc()).limit(1000).all()
        for name_raw, url, p_id in products:
            name = (name_raw or '').strip() or 'Unknown Shop'
            if name not in shops:
                shop_url = None
                if url and 'shopee.vn' in url:
                    m = re.search(r'/product/(\d+)/\d+', url)
                    if m: shop_url = f"https://shopee.vn/shop/{m.group(1)}"
                shops[name] = {'shop_name': name, 'shop_url': shop_url, 'count': 0, 'last_crawled': f"product_{p_id}"}
            shops[name]['count'] += 1
            
        # 3. Fallback to shops.json
        try:
            registry_path = os.path.abspath(os.path.join(base_dir, '..', 'data', 'shops.json'))
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    saved_map = _json.load(f)
                    for n, v in saved_map.items():
                        if n not in shops:
                            shops[n] = {'shop_name': n, 'shop_url': v.get('shop_url'), 'count': 0}
                        elif v.get('shop_url') and not shops[n]['shop_url']:
                            shops[n]['shop_url'] = v.get('shop_url')
        except Exception: pass

        # Sort by last_crawled desc - ensure string comparison
        items = sorted(shops.values(), key=lambda x: str(x.get('last_crawled') or ''), reverse=True)
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

        # Also update historical shops table if it exists
        try:
            import sqlite3
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE shops SET display_name = ? WHERE display_name = ?", (new, old))
                conn.commit()
                conn.close()
        except Exception as e:
            current_app.logger.warning(f"History table update failed on rename: {e}")

        # Also update shops.json if it exists
        try:
            registry_path = os.path.abspath(os.path.join(base_dir, '..', 'data', 'shops.json'))
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    s_map = _json.load(f)
                if old in s_map:
                    val = s_map.pop(old)
                    val['shop_name'] = new
                    s_map[new] = val
                    with open(registry_path, 'w', encoding='utf-8') as f:
                        _json.dump(s_map, f, ensure_ascii=False, indent=2)
        except Exception: pass
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
            'clean_image_path': product.clean_image_path,
            'price': product.price,
            'category': product.item_type.name if product.item_type else product.category_label,
            'sub_category': product.category.name if product.category else product.sub_category_label,
            'style': product.style_ref.name if product.style_ref else product.style_label,
            'shop_name': product.shop_name,
            'product_url': product.product_url,
            'shopee_url': getattr(product, "shopee_url", None) or product.product_url,
            'style_tag': getattr(product, "style_tag", None),
            'body_shape_tag': getattr(product, "body_shape_tag", None),
            'color': product.color.name if product.color else (product.color_primary or product.color_label),
            'color_primary': product.color_primary,
            'color_secondary': product.color_secondary,
            'hex_primary': product.hex_primary,
            'color_tone': product.color.tone if product.color else product.color_tone,
            'season': product.season_ref.name if product.season_ref else (product.season or product.season_label or 'All-season'),
            'occasion': product.occasion_ref.name if product.occasion_ref else (product.occasion or product.occasion_label or 'Daily wear'),
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
        
        # Sửa lỗi cập nhật ảnh: Chạy YOLO làm sạch trong luồng riêng để KHÔNG gây lag UI
        if 'image' in data or 'image_url' in data:
            new_img = data.get('image') or data.get('image_url')
            if new_img and new_img != product.image_url:
                product.image_url = new_img
                
                # Chạy dọn dẹp ảnh ngầm (background) để tránh nghẽn thread chính của Flask
                import threading
                def clean_bg(img_url, item_id, pid):
                    with current_app.app_context():
                        try:
                            # Cần query lại product trong thread mới
                            p = Product.query.get(pid)
                            if p:
                                cleaned = _clean_image_with_yolo(img_url, item_id)
                                if cleaned:
                                    p.clean_image_path = cleaned
                                    db.session.commit()
                        except Exception as e:
                            print(f"[BG YOLO] Failed for item {item_id}: {e}")

                threading.Thread(target=clean_bg, args=(new_img, product.item_id, product.id)).start()

        if 'product_url' in data or 'link' in data:
            new_link = data.get('product_url') or data.get('link')
            if new_link:
                product.product_url = new_link
                try:
                    product.shopee_url = new_link
                except Exception:
                    pass
        
        if 'shopee_url' in data:
            product.shopee_url = data['shopee_url']
            if not product.product_url:
                product.product_url = data['shopee_url']
        elif 'shopee_link' in data:
            product.product_url = data['shopee_link']
            try:
                product.shopee_url = data['shopee_link']
            except Exception:
                pass
        if 'shop_name' in data:
            product.shop_name = data['shop_name']
        if 'gender' in data:
            product.gender = data['gender']
        if 'occasion' in data:
            try:
                product.occasion = data['occasion']
            except Exception:
                pass
        if 'style_tag' in data:
            try:
                product.style_tag = data['style_tag']
            except Exception:
                pass
        if 'body_shape_tag' in data:
            try:
                product.body_shape_tag = data['body_shape_tag']
            except Exception:
                pass
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
                sub_category_name = sub_category_name or (product.category.name if product.category else product.sub_category_label or 'Other')

            item_type_name, sub_category_name = validate_and_fix_category(product.name, item_type_name, sub_category_name)

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


def _run_vton_pipeline(in_path, garment_path, garment_type, recommended, cat, results_dir, out_path):
    """
    Core VTON logic to be run in the worker thread.
    """
    is_fallback = True
    final_path = in_path

    try:
        # Determine Rendering Flow (Single vs 2-Step)
        if garment_type.lower() == "full outfit":
            print("[TRYON] Full Outfit detected. Starting 2-step process...")
            
            # Step 1: Find a TOP (Robust detection)
            top_item = next((x for x in recommended if any(k in str(x.get("garment_type") or "").lower() for k in ["top", "ao", "áo", "shirt", "t-shirt", "vest", "khoác"])), None)
            # Step 2: Find a BOTTOM (Robust detection)
            bottom_item = next((x for x in recommended if any(k in str(x.get("garment_type") or "").lower() for k in ["bottom", "quan", "quần", "pants", "short", "jeans", "trouser"])), None)
            
            current_person_path = in_path
            
            # Render Top
            if top_item:
                print(f"[TRYON] Step 1: Applying TOP {top_item['name']}")
                clean_path = _resolve_clean_abs(top_item.get('clean_image_path'))
                t_garment_raw = clean_path if clean_path else download_garment_image(top_item['image_url'], top_item.get('shopee_url'))
                if t_garment_raw:
                    processed_dir = os.path.join(current_app.static_folder, 'uploads', 'tryon', 'processed')
                    t_garment = process_garment_for_vton(t_garment_raw, processed_dir) or t_garment_raw
                    res_top, fb_top = call_fashn_vton(current_person_path, t_garment, category="tops")
                    
                    if fb_top or _get_image_similarity(current_person_path, res_top) > 0.85:
                        print("[TRYON] Top render failed or unchanged. Trying IDM-VTON fallback...")
                        res_top, fb_top = call_idm_vton(current_person_path, t_garment)
                    
                    if not fb_top:
                        current_person_path = res_top
                        is_fallback = False
            
            # Render Bottom
            if bottom_item:
                print(f"[TRYON] Step 2: Applying BOTTOM {bottom_item['name']}")
                clean_path = _resolve_clean_abs(bottom_item.get('clean_image_path'))
                b_garment_raw = clean_path if clean_path else download_garment_image(bottom_item['image_url'], bottom_item.get('shopee_url'))
                if b_garment_raw:
                    processed_dir = os.path.join(current_app.static_folder, 'uploads', 'tryon', 'processed')
                    b_garment = process_garment_for_vton(b_garment_raw, processed_dir) or b_garment_raw
                    res_bottom, fb_bottom = call_fashn_vton(current_person_path, b_garment, category="bottoms")
                    
                    if fb_bottom or _get_image_similarity(current_person_path, res_bottom) > 0.85:
                        print("[TRYON] Bottom render failed or unchanged. Trying IDM-VTON fallback...")
                        res_bottom, fb_bottom = call_idm_vton(current_person_path, b_garment)

                    if not fb_bottom:
                        final_path = res_bottom
                        is_fallback = False
                    else:
                        final_path = current_person_path # Keep top only if bottom fails
            else:
                final_path = current_person_path

        else:
            # Single Item Try-On (Default)
            res_path, fb = call_fashn_vton(in_path, garment_path, category=cat) if garment_path else (in_path, True)
            
            # If FASHN failed, try IDM-VTON immediately
            if fb and garment_path:
                print("[TRYON] FASHN VTON failed. Trying IDM-VTON...")
                res_path, fb = call_idm_vton(in_path, garment_path)

            # FIX BUG 1: Similarity Check -> Re-run with IDM-VTON as fallback if FASHN didn't change anything
            if not fb:
                sim = _get_image_similarity(in_path, res_path)
                print(f"[TRYON] Output similarity: {sim:.2%}")
                if sim > 0.85:
                    print("[TRYON] Image didn't change enough (>85% similar). Trying IDM-VTON fallback...")
                    res_path, fb = call_idm_vton(in_path, garment_path)
            
            final_path = res_path
            is_fallback = fb

        # Copy to final out_path
        shutil.copyfile(final_path, out_path)
        return {"path": out_path, "is_fallback": is_fallback}
        
    except Exception as ai_err:
        print(f"[TRYON] Pipeline error: {ai_err}")
        shutil.copyfile(in_path, out_path)
        return {"path": out_path, "is_fallback": True}

@main_bp.route('/api/virtual-tryon', methods=['POST'])
def virtual_tryon_api():
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'message': 'photo is required'}), 400

        photo = request.files['photo']
        if not photo or not photo.filename:
            return jsonify({'success': False, 'message': 'photo is required'}), 400

        if not _is_allowed_image_file(photo):
            return jsonify({'success': False, 'message': 'Only JPG/PNG/WEBP are supported'}), 400

        gender = (request.form.get('gender') or 'female').strip()
        occasion = (request.form.get('occasion') or 'casual').strip()
        style = (request.form.get('style') or 'any').strip()
        body_shape = (request.form.get('body_shape') or '').strip()
        budget = (request.form.get('budget') or 'any').strip()
        garment_type = (request.form.get('garment_type') or 'any').strip()

        # Folders
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'tryon')
        results_dir = os.path.join(current_app.static_folder, 'static', 'tryon_results')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)

        # Save Person Image
        ext = os.path.splitext(photo.filename)[1].lower() or '.jpg'
        in_name = f"{uuid.uuid4().hex}{ext}"
        in_path = os.path.join(upload_dir, in_name)
        photo.save(in_path)

        # 1. Get filtered outfits
        recommended = get_recommended_outfits(
            gender=gender,
            occasion=occasion,
            style=style,
            body_shape=body_shape,
            budget=budget,
            garment_type=garment_type,
            limit=6,
        )

        if not recommended:
             recommended = _get_demo_products()

        def _resolve_clean_abs(clean_rel):
            if not clean_rel: return None
            try:
                rel = str(clean_rel).lstrip("/").replace("\\", "/")
                abs_path = os.path.abspath(os.path.join(current_app.static_folder, rel))
                if os.path.exists(abs_path): return abs_path
            except: pass
            return None

        # 2. Pick garment image
        candidates = recommended
        if garment_type and garment_type.lower() != "any":
            gt = garment_type.lower()
            matched = [x for x in candidates if str(x.get("garment_type") or "").lower().startswith(gt)]
            if matched: candidates = matched

        best_match = next((x for x in candidates if _resolve_clean_abs(x.get("clean_image_path"))), None)
        if not best_match:
            best_match = next((x for x in candidates if str(x.get('image_url') or '').startswith('http')), None) or candidates[0]

        garment_url = best_match.get('image_url')
        shopee_url = best_match.get('shopee_url')
        
        clean_abs = _resolve_clean_abs(best_match.get("clean_image_path"))
        garment_raw_path = clean_abs or (download_garment_image(garment_url, shopee_url) if garment_url else None)
        
        garment_path = None
        if garment_raw_path and os.path.exists(garment_raw_path):
            processed_dir = os.path.join(current_app.static_folder, 'uploads', 'tryon', 'processed')
            garment_path = process_garment_for_vton(garment_raw_path, processed_dir) or garment_raw_path

        # Determine fashn_category correctly
        db_cat = str(best_match.get("category_label") or best_match.get("category") or "")
        fashn_cat = map_category_to_fashn(db_cat)
        
        # Override if user explicitly picked a garment type in the UI
        if garment_type and garment_type.lower() != "any" and garment_type.lower() != "full outfit":
            fashn_cat = map_garment_type_to_fashn(garment_type)

        print(f"[TRYON] Using FASHN Category: {fashn_cat} (from DB: {db_cat})")

        # Cache Check (md5 hash of person and garment)
        import hashlib
        def _get_file_hash(path):
            with open(path, "rb") as f: return hashlib.md5(f.read()).hexdigest()

        person_hash = _get_file_hash(in_path)
        garment_id = best_match.get("id", "none")
        cache_key = hashlib.md5(f"{person_hash}_{garment_id}_{fashn_cat}".encode()).hexdigest()
        
        out_name = f"cache_{cache_key}.jpg"
        out_path = os.path.join(results_dir, out_name)

        if os.path.exists(out_path):
            return jsonify({
                "success": True,
                "result_image_url": f"/static/tryon_results/{out_name}",
                "is_fallback": False,
                "tried_outfit": best_match,
                "recommended_outfits": recommended
            }), 200

        task_id = vton_processor_queue.add_task(
            _run_vton_pipeline,
            in_path, garment_path, garment_type, recommended, fashn_cat, results_dir, out_path
        )

        # Trả về task_id ngay lập tức để frontend poll
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": "Đã thêm vào hàng đợi xử lý AI..."
        }), 202

    except Exception as e:
        print(f"[API] Error: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@main_bp.route('/api/virtual-tryon/status/<task_id>', methods=['GET'])
def virtual_tryon_status(task_id):
    """Poll for VTON task status."""
    if task_id in vton_processor_queue.results:
        result = vton_processor_queue.results.pop(task_id)
        if result["status"] == "success":
            final_data = result["data"]
            return jsonify({
                "success": True,
                "status": "completed",
                "result_image_url": f"/static/tryon_results/{os.path.basename(final_data['path'])}",
                "is_fallback": final_data["is_fallback"]
            }), 200
        else:
            return jsonify({
                "success": True,
                "status": "failed",
                "message": result.get("message", "AI processing failed")
            }), 200
    
    is_pending = any(t[0] == task_id for t in list(vton_processor_queue.queue.queue))
    if is_pending:
        return jsonify({
            "success": True,
            "status": "pending",
            "message": "Đang chờ đến lượt xử lý..."
        }), 200
        
    return jsonify({"success": False, "message": "Task not found"}), 404

@main_bp.route('/api/admin/normalized-selected', methods=['GET'])
def get_normalized_selected():
    """Lấy danh sách các sản phẩm trong hàng đợi chuẩn hóa."""
    from .models import NormalizedProduct, Product
    
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    
    query = NormalizedProduct.query
    if status_filter:
        query = query.filter(NormalizedProduct.status == status_filter)
    if category_filter:
        query = query.filter(NormalizedProduct.category == category_filter)

        
    normalized_list = query.order_by(NormalizedProduct.created_at.desc()).all()
    
    results = []
    for item in normalized_list:
        results.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name if item.product else "Unknown",
            "original_image": item.original_image_url,
            "normalized_image": item.normalized_image_path,
            "category": item.category,
            "status": item.status,
            "updated_at": item.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "clean_image_paths": _json.loads(item.product.clean_image_paths) if item.product and item.product.clean_image_paths else []
        })
        
    return jsonify({"success": True, "data": results})

@main_bp.route('/api/admin/normalize-selected/add', methods=['POST'])
def add_to_normalized_queue():
    """Thêm hoặc cập nhật các sản phẩm được chọn từ Product List vào hàng đợi chuẩn hóa."""
    from .models import NormalizedProduct, Product
    data = request.get_json()
    product_ids = data.get("product_ids", [])
    
    if not product_ids:
        return jsonify({"success": False, "message": "No products selected"}), 400
        
    added_count = 0
    for pid in product_ids:
        # Nếu đã tồn tại, chúng ta reset lại trạng thái thay vì bỏ qua
        existing = NormalizedProduct.query.filter_by(product_id=pid).first()
        product = Product.query.get(pid)
        if not product:
            continue

        if existing:
            # Reset trạng thái về pending và cập nhật lại ảnh gốc mới nhất
            existing.status = "pending"
            existing.original_image_url = product.image_url
            existing.normalized_image_path = None # Xóa ảnh cũ để giao diện hiển thị đúng
            added_count += 1
        else:
            new_item = NormalizedProduct(
                product_id=pid,
                original_image_url=product.image_url,
                status="pending"
            )
            db.session.add(new_item)
            added_count += 1
                
    db.session.commit()
    return jsonify({"success": True, "added": added_count})

from .background_tasks import normalization_queue, normalization_status

@main_bp.route('/api/admin/normalize-selected/run', methods=['POST'])
def run_normalization_selected():
    """Bắt đầu quá trình chuẩn hóa nền."""
    if normalization_status["is_running"]:
        return jsonify({"success": False, "message": "A normalization process is already running."}), 400

    data = request.get_json()
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"success": False, "message": "No items selected for normalization"}), 400

    # Đặt lại trạng thái và bắt đầu
    normalization_status["is_running"] = True
    normalization_status["processed"] = 0
    normalization_status["total"] = len(ids)
    normalization_status["status"] = "Running"

    for item_id in ids:
        normalization_queue.put(item_id)
        
    return jsonify({
        "success": True, 
        "message": f"Started normalization for {len(ids)} items. You can monitor the progress on the button below.",
        "processed": 0,
        "total": len(ids)
    })

@main_bp.route('/api/admin/normalize-selected/status', methods=['GET'])
def get_normalization_status():
    """Lấy trạng thái hiện tại của quá trình chuẩn hóa."""
    return jsonify(normalization_status)

@main_bp.route('/api/admin/normalize-selected/delete', methods=['POST'])
def delete_normalized_items():
    """Xóa các item khỏi tab Normalized Selected."""
    from .models import NormalizedProduct
    data = request.get_json()
    ids = data.get("ids", [])
    
    if not ids:
        return jsonify({"success": False, "message": "No items selected"}), 400
        
    items = NormalizedProduct.query.filter(NormalizedProduct.id.in_(ids)).all()
    for item in items:
        db.session.delete(item)
        
    db.session.commit()
    return jsonify({"success": True, "deleted": len(items)})

@main_bp.route('/api/admin/remove-background-only', methods=['POST'])
def remove_background_manual():
    """Chỉ thực hiện tách nền (Rembg) cho một sản phẩm cụ thể (Manual choice)."""
    data = request.get_json()
    product_id = data.get("product_id")
    mode = data.get("mode", "standard") # 'standard' (u2netp) hoặc 'cloth' (u2net_cloth_seg)

    if not product_id:
        return jsonify({"success": False, "message": "Product ID required"}), 400

    from .models import Product
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404

    try:
        from .ai.product_processor import extract_main_product
        from .utils import download_garment_image
        
        # 1. Download ảnh gốc nếu chưa có local hoặc dùng URL
        img_url = product.image_url
        local_raw = download_garment_image(img_url, product.product_url)
        if not local_raw:
             return jsonify({"success": False, "message": "Failed to download image"}), 500

        # 2. Xử lý tách nền
        processed_dir = os.path.join(current_app.static_folder, 'uploads', 'cleaned')
        os.makedirs(processed_dir, exist_ok=True)
        
        out_name = f"manual_clean_{product_id}_{uuid.uuid4().hex[:8]}.png"
        out_path = os.path.join(processed_dir, out_name)
        
        # Chọn model tùy theo mode
        model_name = "u2net_cloth_seg" if mode == "cloth" else "u2netp"
        
        print(f"[Manual BG] Mode: {model_name} | Input: {local_raw}")
        result_path = extract_main_product(local_raw, out_path, model_name=model_name)
        
        if result_path and os.path.exists(result_path):
            rel_path = f"/uploads/cleaned/{out_name}"
            product.clean_image_path = rel_path
            product.norm_status = 'clean'
            
            # CẬP NHẬT: Đồng bộ sang bảng NormalizedProduct nếu có
            from .models import NormalizedProduct
            norm_item = NormalizedProduct.query.filter_by(product_id=product_id).first()
            if norm_item:
                norm_item.normalized_image_path = rel_path
                norm_item.status = 'processed'
                # Cố gắng phân loại lại nếu chưa có category
                if not norm_item.category or norm_item.category == 'N/A':
                    from .background_tasks import infer_canonical_category_by_name, map_category_to_fashn
                    db_cat, _ = infer_canonical_category_by_name(product.name)
                    norm_item.category = map_category_to_fashn(db_cat)
            
            db.session.commit()
            return jsonify({
                "success": True, 
                "message": "Background removed successfully!",
                "clean_image_path": rel_path
            })
        else:
            return jsonify({"success": False, "message": "AI processing failed"}), 500
            
    except Exception as e:
        print(f"[Manual BG] Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

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
    shop_url     = (data.get("shop_url") or "").strip()
    shop_name    = data.get("shop_name", "")
    target_count = int(data.get("target_count", 40))
    save_to_db   = data.get("save_to_db", True) # Default remains True for backward compatibility

    if not shop_url:
        return jsonify({"success": False, "error": "Missing shop_url", "products": []}), 400

    try:
        # Use the newly downloaded stealth crawlers
        logger = current_app.logger
        products = []
        
        if 'shopee.vn' in shop_url:
            logger.info(f"Using Shopee stealth crawler for {shop_url}")
            products = crawl_shopee(shop_url, limit=target_count)
        elif 'lazada.vn' in shop_url:
            logger.info(f"Using Lazada stealth crawler for {shop_url}")
            products = crawl_lazada(shop_url, limit=target_count)
        
        if not products:
            if 'shopee.vn' in shop_url:
                # Fallback to old playwright crawler for Shopee if stealth crawler fails
                logger.info("Stealth crawler returned no results, falling back to Playwright crawler...")
                result = crawl_shopee_new(shop_url, target_count=target_count)
            else:
                result = {"success": False, "error": "No products found", "products": []}
        else:
            # Normalize for DB compatibility
            normalized_products = []
            for p in products:
                item_id = str(p.get("itemid", ""))
                shop_id = str(p.get("shopid", ""))
                # Use format consistent with old crawler: {shop_id}_{item_id}
                p["id"] = f"{shop_id}_{item_id}" if shop_id and item_id else item_id
                # Ensure image_url key exists
                p["image_url"] = p.get("image", "")
                # Ensure price_display exists
                p["price_display"] = f"{int(p.get('price', 0)):,}đ".replace(",", ".")
                # Ensure shop_name exists
                p["shop_name"] = shop_name or p.get("shop_name")
                normalized_products.append(p)

            # Prepare result in the format the route expects
            result = {
                "success": True,
                "products": normalized_products,
                "shop_id": products[0].get("shopid") if products else None,
                "total_crawled": len(products)
            }

        if not result["success"]:
            return jsonify({
                "success": False,
                "error": result.get("error") or "No products found",
                "products": [],
                "log": [
                    f"> [1/2] Connecting to: {shop_url[:80]}...",
                    f"> [2/2] FAILED: {result.get('error') or 'Empty result'}",
                ]
            })

        saved = 0
        if save_to_db:
            # Sync shop_name into product objects
            if shop_name:
                for p in result.get("products", []):
                    if not p.get("shop_name"):
                        p["shop_name"] = shop_name
            saved = save_products_to_db(result["products"])
            
            # Post-crawl processing: Clean Images + AI Tagging
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
                
                # Step 1: Clean images (tách ảnh ghép)
                try:
                    batch_clean_from_db(db_path, limit=saved)
                except Exception as ce:
                    print(f"[Cleaner] Image cleaning failed: {ce}")
                
                # Step 2: AI tagging (gán màu, nhãn) - Gọi theo hướng dẫn BƯỚC 3
                try:
                    tag_all_products(db_path=db_path, limit=saved)
                except Exception as te:
                    print(f"[Tagger] Product tagging failed: {te}")

            except Exception as pe:
                print(f"Post-crawl processing failed: {pe}")

        # ALWAYS save or update shop history info when a crawl is performed
        if result.get("shop_id") and (shop_name or shop_url):
            try:
                import sqlite3
                base_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
                
                conn = sqlite3.connect(db_path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS shops 
                    (shop_id TEXT PRIMARY KEY, display_name TEXT, shop_url TEXT,
                        last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                """)
                d_name = shop_name or f"Shopee Shop {result['shop_id']}"
                conn.execute("""
                    INSERT OR REPLACE INTO shops (shop_id, display_name, shop_url, last_crawled)
                    VALUES (?,?,?, CURRENT_TIMESTAMP)
                """, (result["shop_id"], d_name, shop_url))
                conn.commit()
                conn.close()
                
                # Sync with legacy shops.json for complete coverage
                registry_path = os.path.abspath(os.path.join(base_dir, '..', 'data', 'shops.json'))
                os.makedirs(os.path.dirname(registry_path), exist_ok=True)
                s_map = {}
                if os.path.exists(registry_path):
                    try:
                        with open(registry_path, 'r', encoding='utf-8') as f: s_map = _json.load(f)
                    except: s_map = {}
                s_map[d_name] = {'shop_name': d_name, 'shop_url': shop_url}
                with open(registry_path, 'w', encoding='utf-8') as f:
                    _json.dump(s_map, f, ensure_ascii=False, indent=2)

            except Exception as e:
                current_app.logger.warning(f"Failed to update shop history: {e}")

        return jsonify({
            "success": True,
            "shop_id": result["shop_id"],
            "total_crawled": result["total_crawled"],
            "saved_to_db": saved,
            "products": result["products"],
            "log": [
                f"> [1/2] Connecting to: {shop_url[:80]}...",
                f"> [2/2] SUCCESS: Found {result['total_crawled']} products! ({saved if save_to_db else 'Not saved'} items)",
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/api/admin/classify-products', methods=['POST'])
def classify_products_route():
    data = request.get_json()
    shop_id = data.get('shop_id')

    # Fetch non-classified products from DB
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
        return jsonify({'message': 'No products to classify', 'classified': 0, 'saved': 0})

    try:
        classified = batch_classify(products, analyze_images=True)
        saved = save_classifications(classified)
        return jsonify({'success': True, 'classified': len(classified), 'saved': saved})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/admin/run-normalization', methods=['POST'])
def run_normalization_route():
    """
    Endpoint for the batch normalization button.
    """
    data = request.get_json() or {}
    limit = int(data.get('limit', 50))
    
    try:
        # Redirect to the new logic if needed, or keep as batch utility
        from data_engine.image_cleaner import batch_clean_from_db
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
        
        cleaned_count = batch_clean_from_db(db_path, limit=limit)
        return jsonify({'success': True, 'cleaned': cleaned_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/crawl/save', methods=['POST'])
def save_crawled_products():
    """Save products from frontend preview to DB using SQLAlchemy for consistency"""
    data = request.get_json()
    products_data = data.get("products", [])
    shop_name = data.get("shop_name", "")
    shop_url = data.get("shop_url", "")

    if not products_data:
        return jsonify({"success": False, "message": "No products to save"}), 400

    try:
        saved_count = 0
        for p_data in products_data:
            item_id = str(p_data.get('id') or p_data.get('item_id'))
            if not item_id: continue
            
            product = Product.query.filter_by(item_id=item_id).first()
            if not product:
                product = Product(item_id=item_id)
                db.session.add(product)
            
            product.name = (p_data.get('name') or '')[:200]
            product.image_url = (p_data.get('image_url') or '')[:500]
            product.product_url = (p_data.get('product_url') or '')[:2000]
            product.price = p_data.get('price')
            product.price_display = p_data.get('price_display')
            product.shop_name = (shop_name or p_data.get('shop_name') or 'Shopee')[:150]
            product.shop_id = str(p_data.get('shop_id') or '')[:100]
            product.rating = float(p_data.get('rating') or 0)
            product.sold_count = int(p_data.get('sold_count') or 0)
            product.is_active = True
            product.is_valid = True
            
            # Category Mapping
            shopee_cat = p_data.get('category')
            it_name, sub_cat = map_to_canonical_clothing(
                ai_category=None, 
                item_type_raw=None, 
                shopee_cat=shopee_cat
            )
            
            if not it_name:
                # Try infer by name
                it_name, sub_cat = infer_canonical_category_by_name(product.name)

            product.category_label = it_name or 'Other'
            product.sub_category_label = sub_cat or 'Other'
            
            # Set foreign keys
            item_type = ItemType.query.filter_by(name=product.category_label).first()
            if item_type:
                product.item_type_id = item_type.id
                category = Category.query.filter_by(name=product.sub_category_label, item_type_id=item_type.id).first()
                if category:
                    product.category_id = category.id
            
            saved_count += 1

        # Save shop info if shop_id exists
        if products_data and (products_data[0].get("shop_id") or shop_name):
            s_id = str(products_data[0].get("shop_id") or "")
            d_name = shop_name or f"Shop {s_id}"
            
            # Update shops table via raw SQL or SQLAlchemy if model exists
            # We use raw SQL for shops table as it might not be a full model yet
            import sqlite3
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'database', 'database_v2.db'))
            
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS shops 
                    (shop_id TEXT PRIMARY KEY, display_name TEXT, shop_url TEXT,
                     last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO shops (shop_id, display_name, shop_url, last_crawled)
                    VALUES (?,?,?, CURRENT_TIMESTAMP)
                """, (s_id, d_name, shop_url))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Failed to save shop info: {e}")

        db.session.commit()

        return jsonify({
            "success": True, 
            "saved_count": saved_count,
            "message": f"Successfully saved {saved_count} products"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

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
