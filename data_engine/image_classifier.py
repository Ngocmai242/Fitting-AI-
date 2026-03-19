import io
import numpy as np
from PIL import Image
import requests
import os
import sys

# Define locations
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Check for AI libraries
try:
    from backend.app.ai.pose import extract_keypoints
except ImportError:
    extract_keypoints = None

try:
    from ultralytics import YOLO
    _yolo_model = None
    def get_yolo():
        global _yolo_model
        if _yolo_model is None:
            # Nano model is fast/light for classification
            try:
                _yolo_model = YOLO('yolov8n.pt')
            except:
                return None
        return _yolo_model
except ImportError:
    get_yolo = lambda: None

def detect_human(image_bytes):
    """
    Returns True if at least one human is present.
    """
    if extract_keypoints is not None:
        try:
            keypoints, error = extract_keypoints(image_bytes, max_people=2)
            if isinstance(keypoints, list) and len(keypoints) > 0:
                return True
        except Exception:
            pass
            
    # Fallback to YOLO class 0 (person) if MediaPipe fails
    model = get_yolo()
    if model:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            results = model(img, verbose=False)
            for r in results:
                for box in r.boxes:
                    if int(box.cls[0]) == 0: # person
                        return True
        except:
            pass
            
    return False

def is_simple_background(image_pill, threshold=0.7):
    """
    Analyze pixel consistency at edges to determine if it's a simple background.
    """
    try:
        img = image_pill.convert("RGB")
        w, h = img.size
        edge_px = []
        for x in range(0, w, 10): 
            edge_px.append(img.getpixel((x, 0)))
            edge_px.append(img.getpixel((x, h-1)))
        for y in range(0, h, 10): 
            edge_px.append(img.getpixel((0, y)))
            edge_px.append(img.getpixel((w-1, y)))
            
        if not edge_px: return False
            
        from collections import Counter
        groups = [(p[0]//20, p[1]//20, p[2]//20) for p in edge_px]
        counts = Counter(groups)
        _, top_count = counts.most_common(1)[0]
        
        ratio = top_count / len(edge_px)
        white_px = sum(1 for p in edge_px if all(c > 225 for c in p))
        white_ratio = white_px / len(edge_px)
        
        return ratio > threshold or white_ratio > 0.6
    except Exception:
        return False

def classify_image_type(image_bytes):
    """
    Returns: 'flat', 'model', 'multiple_items', 'overlapping_set', 'unknown'
    """
    # 1. Human check (MediaPipe or YOLO)
    if detect_human(image_bytes):
        return 'model'
    
    # 2. YOLO object count & bounding box analysis
    model = get_yolo()
    if model:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            results = model(img, verbose=False)
            boxes = []
            for r in results:
                for box in r.boxes:
                    # COCO classes relevant to clothing/items:
                    # 24: backpack, 26: handbag, 27: tie, 28: suitcase, 0: person
                    # We usually want anything that isn't background.
                    # For clothingเฉพาะ, we might need a custom model.
                    # But for now, let's use standard detections.
                    boxes.append(box.xyxy[0].tolist())
            
            if len(boxes) > 1:
                # Check for overlap
                overlaps = False
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        # Simple AABB overlap check
                        b1 = boxes[i]
                        b2 = boxes[j]
                        if not (b1[2] < b2[0] or b1[0] > b2[2] or b1[3] < b2[1] or b1[1] > b2[3]):
                            overlaps = True
                            break
                    if overlaps: break
                
                if overlaps:
                    return 'overlapping_set'
                else:
                    return 'multiple_items'
        except:
            pass

    # 3. Simple background check
    try:
        img_pill = Image.open(io.BytesIO(image_bytes))
        if is_simple_background(img_pill):
            return 'flat'
    except:
        pass
        
    return 'unknown'

