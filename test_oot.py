from gradio_client import Client, handle_file
import os

def test_oot():
    try:
        print("Testing OOTDiffusion...")
        client = Client("levihsu/OOTDiffusion")
        person = os.path.abspath("backend/test_person.jpg")
        garment = os.path.abspath("backend/test_garment.jpg")
        
        result = client.predict(
            vton_img=handle_file(person),
            garm_img=handle_file(garment),
            category="Upper-body",
            n_samples=1,
            n_steps=20,
            image_scale=2.0,
            seed=-1,
            api_name="/process_dc"
        )
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_oot()
