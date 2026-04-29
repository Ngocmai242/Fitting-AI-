import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
person_path = os.path.join(os.path.dirname(__file__), "test_p.png")
garment_path = os.path.join(os.path.dirname(__file__), "test_g.png")

from app.routes import call_hf_kolors_vton_api
print(call_hf_kolors_vton_api(person_path, garment_path))
