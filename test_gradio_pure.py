from gradio_client import Client, handle_file
import os

def test_outfit_anyone():
    try:
        print("Testing OutfitAnyone...")
        client = Client("humanAIGC/OutfitAnyone")
        print("Client loaded!")
        person = os.path.abspath("backend/test_person.jpg")
        garment = os.path.abspath("backend/test_garment.jpg")
        
        result = client.predict(
            model_name=handle_file(person),
            garment1=handle_file(garment),
            garment2=handle_file(garment),
            api_name="/get_tryon_result"
        )
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_outfit_anyone()
