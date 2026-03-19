import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from . import db
from .models import NormalizedProduct
from .ai.product_processor import process_garment_for_vton
from .utils import download_garment_image
import os
import time
import unicodedata

# Hàng đợi xử lý nền
normalization_queue = queue.Queue()
normalization_status = {
    "is_running": False,
    "processed": 0,
    "total": 0,
    "status": "Idle"
}

# Sử dụng Lock để cập nhật normalization_status an toàn giữa các luồng
status_lock = threading.Lock()

def _norm_ascii(s: str) -> str:
    if not s: return ""
    s = s.lower().strip()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd')

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

def map_category_to_fashn(db_category: str) -> str:
    if not db_category:
        return "tops"
    cat = str(db_category).lower().strip()
    if cat.startswith("bottoms") or any(x in cat for x in ["quần", "jean", "jeans", "pants", "trousers", "shorts", "skirt", "legging"]):
        return "bottoms"
    if any(x in cat for x in ["dress", "one-piece", "jumpsuit", "romper", "đầm", "váy liền", "vay", "dam"]):
        return "one-pieces"
    return "tops"

def process_single_item(item_id, app):
    """Hàm xử lý cho một sản phẩm, được thiết kế để chạy trong một luồng riêng biệt."""
    with app.app_context():
        # Lấy lại object từ session của app_context này
        item = db.session.get(NormalizedProduct, item_id)
        if not item:
            return False

        try:
            # Cập nhật trạng thái bắt đầu xử lý
            with status_lock:
                normalization_status["status"] = f"Processing item {item_id}"
            
            item.status = "processing"
            db.session.commit()

            garment_url = item.original_image_url
            shopee_url = item.product.shopee_url if item.product else None
            
            print(f"[Worker] Processing item {item_id} | URL: {garment_url[:40]}...")
            
            if not garment_url and not shopee_url:
                print(f"[Worker] Error: No URL for item {item_id}")
                item.status = "failed"
                db.session.commit()
                return False

            local_raw = download_garment_image(garment_url, shopee_url)
            if not local_raw:
                print(f"[Worker] Error: Download failed for item {item_id}")
                item.status = "failed"
                db.session.commit()
                return False

            norm_dir = os.path.join(current_app.static_folder, 'static', 'normalized_selected')
            os.makedirs(norm_dir, exist_ok=True)
            
            # Xử lý ảnh (RemBG, Inpainting, Resize)
            print(f"[Worker] Running AI processing for item {item_id}...")
            norm_path = process_garment_for_vton(local_raw, norm_dir)
            
            if norm_path:
                print(f"[Worker] AI processing successful! Saved to: {norm_path}")
                item.normalized_image_path = f"/static/normalized_selected/{os.path.basename(norm_path)}"
                
                # Phân loại lại dựa trên tên sản phẩm
                product_name = item.product.name if item.product else ""
                db_cat, _ = infer_canonical_category_by_name(product_name)
                
                # Map sang format Fashn VTON
                item.category = map_category_to_fashn(db_cat)
                item.status = "processed"
                
                # Lưu vào DB
                db.session.add(item)
                db.session.commit()
                return True
            else:
                print(f"[Worker] AI processing failed (no output) for item {item_id}")
                item.status = "failed"
                db.session.commit()
                return False
        except Exception as e:
            app.logger.error(f"Error processing item {item_id}: {e}")
            print(f"[Worker] EXCEPTION mapping item {item_id}: {e}")
            try:
                db.session.rollback()
                failed_item = db.session.get(NormalizedProduct, item_id)
                if failed_item:
                    failed_item.status = "failed"
                    db.session.commit()
            except: pass
            
            with status_lock:
                normalization_status["last_error"] = str(e)
            return False
        finally:
            with status_lock:
                normalization_status["processed"] += 1


def worker_manager(app):
    """Quản lý việc lấy từ hàng đợi và phân phối cho ThreadPoolExecutor."""
    # Tăng số lượng worker lên 4-8 để xử lý song song
    # Lưu ý: Không nên quá cao vì RemBG/AI tốn CPU/RAM
    max_workers = 4 
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while True:
            try:
                # Lấy tất cả item hiện có trong queue để xử lý theo đợt
                items_to_process = []
                while not normalization_queue.empty():
                    item_id = normalization_queue.get()
                    if item_id is None: break
                    items_to_process.append(item_id)
                
                if items_to_process:
                    # Gửi tất cả item vào pool để xử lý song song và CHỜ đến khi đợt này xong hết mới đi tiếp
                    # Việc dùng list() ép generator phải thực thi xong các task
                    print(f"[Worker Manager] Starting batch of {len(items_to_process)} items...")
                    list(executor.map(lambda x: process_single_item(x, app), items_to_process))
                    print(f"[Worker Manager] Batch finished.")
                
                # Nghỉ một chút trước khi check queue tiếp
                time.sleep(1)
                
                # Tự động reset trạng thái nếu thực sự đã xong hết tất cả các task đã nhận
                with status_lock:
                    if normalization_queue.empty() and normalization_status["processed"] >= normalization_status["total"]:
                        if normalization_status["is_running"]:
                            print(f"[Worker Manager] All tasks completed ({normalization_status['processed']}/{normalization_status['total']}). Going Idle.")
                            normalization_status["is_running"] = False
                            normalization_status["status"] = "Idle"
                        
            except Exception as e:
                print(f"[Worker Manager] Error: {e}")
                time.sleep(5)

def start_worker(app):
    """Khởi chạy trình quản lý worker trong một luồng daemon."""
    manager_thread = threading.Thread(target=worker_manager, args=(app,))
    manager_thread.daemon = True
    manager_thread.start()

