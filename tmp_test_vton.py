import os
import sys

# Setup path so it can import from backend.app
sys.path.append(os.path.abspath("backend"))

from app import create_app
from app.routes import _run_vton_pipeline_v2
import uuid
from flask import current_app

def run_test():
    app = create_app()
    with app.app_context():
        # Lấy file ảnh test từ backend/test_p.png và backend/test_g.png (nếu có)
        # Hoặc dùng absolute url
        import urllib.request
        person_path = os.path.abspath("backend/test_person.jpg")
        garment_path = os.path.abspath("backend/test_garment.jpg")
        
        # Download test images if not exist
        if not os.path.exists(person_path):
            urllib.request.urlretrieve("https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=512", person_path)
        if not os.path.exists(garment_path):
            urllib.request.urlretrieve("https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=512", garment_path)
            
        print("--- STARTING VTON TEST ---")
        garments = [
            {
                "name": "Test Shirt",
                "clean_image_path": garment_path,
                "category": "tops"
            }
        ]
        
        results_dir = os.path.abspath("frontend/static/tryon_results")
        os.makedirs(results_dir, exist_ok=True)
        out_path = os.path.join(results_dir, f"test_out_{uuid.uuid4().hex}.jpg")
        
        print(f"Person: {person_path}")
        print(f"Garment: {garment_path}")
        
        static_folder_path = os.path.abspath("frontend")
        
        res = _run_vton_pipeline_v2(person_path, garments, results_dir, out_path, static_folder_path, gender="female")
        print("\n--- RESULT ---")
        print(res)

if __name__ == "__main__":
    run_test()
