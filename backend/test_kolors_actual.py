from gradio_client import Client, handle_file
import os

person_path = "c:/Mai/4/backend/test_p.png"
garment_path = "c:/Mai/4/backend/test_g.png"

try:
    print("Testing Kwai-Kolors/Kolors-Virtual-Try-On fn_index=2...")
    client = Client("Kwai-Kolors/Kolors-Virtual-Try-On")
    result = client.predict(
        person_img=handle_file(person_path),
        garment_img=handle_file(garment_path),
        seed=42,
        randomize_seed=False,
        fn_index=2
    )
    print("Success:", result)
except Exception as e:
    print("Error:", e)
