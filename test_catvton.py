from gradio_client import Client, handle_file
import os

def test_catvton():
    try:
        print("Testing CatVTON...")
        client = Client("zhengchong/CatVTON")
        person = os.path.abspath("backend/test_person.jpg")
        garment = os.path.abspath("backend/test_garment.jpg")
        
        result = client.predict(
            dict={"background": handle_file(person), "layers": [], "composite": None},
            garm_img=handle_file(garment),
            garment_des="A nice clothing item",
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
    test_catvton()
