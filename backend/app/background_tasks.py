import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from . import db
from .models import NormalizedProduct
from .utils import (
    download_garment_image,
    _norm_ascii,
    infer_canonical_category_by_name,
    map_category_to_fashn
)
import os
import time
import uuid
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

# Helper functions moved to utils.py

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
            item.error_message = None # Clear old errors
            db.session.commit()

            garment_url = item.original_image_url
            shopee_url = item.product.shopee_url if item.product else None
            
            print(f"[Worker] Processing item {item_id} | URL: {garment_url[:40] if garment_url else 'None'}...")
            
            if not garment_url and not shopee_url:
                err_msg = "Error: No URL provided for item"
                print(f"[Worker] {err_msg} {item_id}")
                item.status = "failed"
                item.error_message = err_msg
                db.session.commit()
                return False

            local_raw = download_garment_image(garment_url, shopee_url)
            if not local_raw:
                err_msg = "Error: Failed to download image from all sources"
                print(f"[Worker] {err_msg} for item {item_id}")
                item.status = "failed"
                item.error_message = err_msg
                db.session.commit()
                return False

            norm_dir = os.path.join(current_app.static_folder, 'static', 'normalized_selected')
            os.makedirs(norm_dir, exist_ok=True)
            
            # Xử lý ảnh (RemBG, Inpainting, Resize)
            print(f"[Worker] Running AI processing for item {item_id}...")
            # Sử dụng segment_clean_images logic hoặc tương đương
            from data_engine.image_classifier import classify_image_type
            from .ai.product_processor import extract_main_product, split_multi_product_image
            
            try:
                with open(local_raw, 'rb') as f: bytes_raw = f.read()
                # Thử phân loại ảnh để chọn model AI phù hợp
                try:
                    img_type = classify_image_type(bytes_raw)
                except Exception as e:
                    print(f"[Worker] Classification failed: {e}. Defaulting to 'flat'")
                    img_type = 'flat'
                
                paths = []
                if img_type in ['multiple_items', 'overlapping_set']:
                    try:
                        paths = split_multi_product_image(local_raw, norm_dir)
                    except Exception as e:
                        print(f"[Worker] Multi-split failed: {e}. Falling back to single extract.")
                        img_type = 'flat' # Thử lại như ảnh đơn
                
                if not paths:
                    out_name = f"vton_garment_{uuid.uuid4().hex}.png"
                    out_path = os.path.join(norm_dir, out_name)
                    
                    # Nếu ảnh có người mẫu, dùng cloth_seg, nếu không dùng isnet-general-use (cực kỳ sạch nền)
                    m_name = "u2net_cloth_seg" if img_type == 'model' else "isnet-general-use"
                    
                    try:
                        res = extract_main_product(local_raw, out_path, model_name=m_name)
                        if res: paths = [res]
                    except Exception as e:
                        print(f"[Worker] Primary extraction failed: {e}. Trying fallback model.")
                        # Fallback cuối cùng sang isnet-general-use nếu cloth_seg bị lỗi
                        try:
                            res = extract_main_product(local_raw, out_path, model_name="isnet-general-use")
                            if res: paths = [res]
                        except Exception as e2:
                            print(f"[Worker] All extraction attempts failed for {item_id}: {e2}")
                            raise e2

                if paths:
                    print(f"[Worker] AI processing successful! Generated {len(paths)} images.")
                    import json
                    rel_list = [f"/static/normalized_selected/{os.path.basename(p)}" for p in paths]
                    primary_rel = rel_list[0]
                    item.normalized_image_path = primary_rel
                    item.normalized_image_paths = json.dumps(rel_list)
                    
                    # Giữ nguyên ảnh gốc ở danh sách chính, chỉ lưu kết quả vào bảng NormalizedProduct
                    # if item.product:
                    #     item.product.clean_image_path = primary_rel
                    #     item.product.clean_image_paths = json.dumps(rel_list)
                    #     item.product.has_model = (img_type == 'model')
                    #     item.product.image_type = img_type
                    
                    # Phân loại lại dựa trên tên sản phẩm
                    product_name = item.product.name if item.product else ""
                    db_cat, _ = infer_canonical_category_by_name(product_name)
                    
                    # Map sang format Fashn VTON
                    item.category = map_category_to_fashn(db_cat)
                    
                    # Cập nhật Photo Type cho Fashn VTON 1.5
                    if img_type == 'model':
                        item.photo_type = 'model'
                    else:
                        item.photo_type = 'flat-lay'
                        
                    item.status = "processed"
                    item.error_message = None
                    
                    # Lưu vào DB
                    db.session.add(item)
                    db.session.commit()
                    return True
                else:
                    raise Exception("AI processing failed to produce any output paths")

            except Exception as ai_err:
                print(f"[Worker] AI Error for item {item_id}: {ai_err}")
                item.status = "failed"
                item.error_message = f"AI Error: {str(ai_err)}"
                db.session.commit()
                return False

        except Exception as e:
            app.logger.error(f"Error processing item {item_id}: {e}")
            print(f"[Worker] CRITICAL EXCEPTION for item {item_id}: {e}")
            try:
                db.session.rollback()
                failed_item = db.session.get(NormalizedProduct, item_id)
                if failed_item:
                    failed_item.status = "failed"
                    failed_item.error_message = f"Critical Exception: {str(e)}"
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

