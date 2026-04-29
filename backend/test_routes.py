import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Tạo file ảnh dummy
person_path = os.path.join(os.path.dirname(__file__), "test_p.png")
garment_path = os.path.join(os.path.dirname(__file__), "test_g.png")

from PIL import Image
Image.new('RGB', (512, 512), color='red').save(person_path)
Image.new('RGB', (512, 512), color='blue').save(garment_path)

from app.routes import call_hf_idmvton_api
print(call_hf_idmvton_api(person_path, garment_path, "test description"))
