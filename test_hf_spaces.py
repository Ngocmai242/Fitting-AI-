from gradio_client import Client, handle_file
import os

def test_spaces():
    spaces_to_test = [
        "Kwai-Kolors/Kolors-Virtual-Try-On", 
        "humanAIGC/OutfitAnyone",
        "levihsu/OOTDiffusion",
        "franciseng/IDM-VTON",
        "yisol/IDM-VTON",
        "fashn-ai/fashn-vton-1.5"
    ]
    person = os.path.abspath("backend/test_person.jpg")
    garment = os.path.abspath("backend/test_garment.jpg")
    
    for space in spaces_to_test:
        print(f"\n--- Testing Space: {space} ---")
        try:
            client = Client(space)
            print("Loaded client.")
            # Note: predict arguments differ per space, this is just to see if Client() throws 401 or ZeroGPU error upon initialization
            # To test ZeroGPU, we MUST make a request.
            # But the args are different. Let's just catch exceptions.
        except Exception as e:
            print(f"Error loading {space}: {e}")

if __name__ == "__main__":
    test_spaces()
