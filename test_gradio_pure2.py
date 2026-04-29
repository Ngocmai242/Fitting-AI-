from gradio_client import Client, handle_file
import os

def test_fashn():
    try:
        print("Testing Fashn...")
        client = Client("fashn-ai/fashn-vton-1.5")
        person = os.path.abspath("backend/test_person.jpg")
        garment = os.path.abspath("backend/test_garment.jpg")
        
        result = client.predict(
            person_image=handle_file(person),
            garment_image=handle_file(garment),
            category="tops",
            garment_photo_type="model",
            num_timesteps=50,
            guidance_scale=2.0,
            seed=42,
            segmentation_free=True,
            api_name="/try_on"
        )
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")

def test_idm():
    try:
        print("Testing IDM-VTON...")
        client = Client("yisol/IDM-VTON")
        person = os.path.abspath("backend/test_person.jpg")
        garment = os.path.abspath("backend/test_garment.jpg")
        
        result = client.predict(
            dict={"background": handle_file(person), "layers": [], "composite": None},
            garm_img=handle_file(garment),
            garment_des="a nice shirt",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fashn()
    test_idm()
