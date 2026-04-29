import os
from gradio_client import Client, handle_file

def test_idm_vton():
    try:
        print("Testing IDM-VTON with token...")
        # Lấy token từ .env
        from dotenv import load_dotenv
        load_dotenv("backend/.env")
        token = os.getenv("HF_TOKEN")
        print(f"Token loaded: {token[:10]}...")
        
        client = Client("yisol/IDM-VTON", token=token)
        print("Client loaded successfully!")
        
        person = os.path.abspath("backend/test_person.jpg")
        garment = os.path.abspath("backend/test_garment.jpg")
        
        result = client.predict(
            dict={"background": handle_file(person), "layers": [], "composite": None},
            garm_img=handle_file(garment),
            garment_des="a nice clothing item",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )
        print(f"Success! Output: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_idm_vton()
