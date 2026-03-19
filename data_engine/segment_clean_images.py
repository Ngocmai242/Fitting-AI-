"""
segment_clean_images.py - Advanced AI Pipeline
- Classifies image (flat, model, multiple, overlapping)
- Applies specialized AI processing for each type
- Supports multiple cleaned images per product
- Stores results in JSON format in clean_image_paths
"""

import argparse
import os
import sqlite3
import json
import uuid
import sys
from io import BytesIO
import numpy as np
import requests
from PIL import Image

# Add project root to path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# AI Imports (handled gracefully)
try:
    from rembg import remove as rembg_remove, new_session
except ImportError:
    rembg_remove = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from data_engine.image_classifier import classify_image_type
from backend.app.ai.product_processor import extract_main_product, split_multi_product_image

def _db_path():
    return os.path.join(_project_root, "database", "database_v2.db")

def _out_dir():
    return os.path.join(_project_root, "frontend", "static", "clean_images")

def _download(url):
    if not url or not url.startswith("http"):
        return None
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.content
    except:
        return None
    return None

def process_flat_image(img_raw, out_filename):
    """Simple background removal for flat-lay images."""
    out_dir = _out_dir()
    out_path = os.path.join(out_dir, out_filename)
    # Using u2netp for speed and accuracy on simple backgrounds
    return [extract_main_product(img_raw, out_path, model_name="u2netp")]

def process_with_human(img_raw, out_filename):
    """Smart garment extraction from model photos."""
    out_dir = _out_dir()
    out_path = os.path.join(out_dir, out_filename)
    # Using u2net_cloth_seg for specialized clothing extraction
    return [extract_main_product(img_raw, out_path, model_name="u2net_cloth_seg")]

def process_multiple_items(img_raw, product_id):
    """Splits grid/multiple item images into individual products."""
    out_dir = _out_dir()
    temp_raw = os.path.join(out_dir, f"temp_{uuid.uuid4().hex}.jpg")
    with open(temp_raw, 'wb') as f:
        f.write(img_raw)
    
    # split_multi_product_image returns list of paths
    paths = split_multi_product_image(temp_raw, out_dir)
    
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
        
    return paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    db_path = _db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    out_dir = _out_dir()
    os.makedirs(out_dir, exist_ok=True)

    # Fetch products that need cleaning
    q = "SELECT id, item_id, image_url FROM products WHERE image_url IS NOT NULL AND image_url != ''"
    if not args.overwrite:
        q += " AND (clean_image_path IS NULL OR clean_image_path = '')"
    q += " LIMIT ?"
    
    rows = cur.execute(q, (args.limit,)).fetchall()
    
    print(f"[SegmentCleaner] Found {len(rows)} products to process.")
    
    ok = 0
    for r in rows:
        pid = r['id']
        url = r['image_url']
        item_id = r['item_id'] or str(pid)
        
        print(f"[SegmentCleaner] Processing {item_id}...")
        raw = _download(url)
        if not raw:
            print(f"  Fail: Download error")
            continue
            
        img_type = classify_image_type(raw)
        print(f"  Type identified: {img_type}")
        
        results = []
        try:
            if img_type == 'flat':
                results = process_flat_image(raw, f"{item_id}.png")
            elif img_type == 'model':
                results = process_with_human(raw, f"{item_id}.png")
            elif img_type in ['multiple_items', 'overlapping_set']:
                # Both cases benefit from splitting/segmenting
                results = process_multiple_items(raw, item_id)
            else:
                # Fallback
                results = process_flat_image(raw, f"{item_id}.png")
        except Exception as e:
            print(f"  AI Error: {e}")
            continue

        if results:
            # Convert abs paths to relative static paths
            clean_paths = []
            for path in results:
                rel = f"static/clean_images/{os.path.basename(path)}"
                clean_paths.append(rel)
            
            # Primary path (usually the first one)
            primary = clean_paths[0]
            paths_json = json.dumps(clean_paths)
            has_model = 1 if img_type == 'model' else 0
            
            cur.execute(
                "UPDATE products SET clean_image_path = ?, clean_image_paths = ?, has_model = ?, image_type = ? WHERE id = ?",
                (primary, paths_json, has_model, img_type, pid)
            )
            ok += 1
            if ok % 10 == 0:
                conn.commit()
            print(f"  Success: Generated {len(clean_paths)} images")
        else:
            print(f"  Fail: No output produced")

    conn.commit()
    conn.close()
    print(f"[SegmentCleaner] Finished. Processed {ok} products.")

if __name__ == "__main__":
    main()
