import os
import sys

# Setup path
sys.path.append(os.path.abspath("backend"))

from app.routes import call_hf_fashn_vton_api, call_hf_outfit_anyone_api, call_hf_kolors_vton_api, call_hf_idmvton_api

def test_apis():
    person = os.path.abspath("backend/test_person.jpg")
    garment = os.path.abspath("backend/test_garment.jpg")
    
    print("Testing OutfitAnyone...")
    res, fb, err = call_hf_outfit_anyone_api(person, garment)
    print(f"OutfitAnyone Result: res={res}, fb={fb}, err={err}")
    
    print("Testing Fashn...")
    res, fb, err = call_hf_fashn_vton_api(person, garment)
    print(f"Fashn Result: res={res}, fb={fb}, err={err}")
    
if __name__ == "__main__":
    test_apis()
