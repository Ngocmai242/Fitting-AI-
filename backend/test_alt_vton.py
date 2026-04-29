from gradio_client import Client, handle_file
import sys, os
person_path = "c:/Mai/4/backend/test_p.png"
garment_path = "c:/Mai/4/backend/test_g.png"
spaces = ["zyflzxy/IDM-VTONS", "cocktailpeanut/IDM-VTON", "allAI-tools/IDM-VTON"]

for s in spaces:
    try:
        print(f"\n--- Testing Space: {s} ---")
        c = Client(s)
        res = c.predict(
            dict={"background": handle_file(person_path), "layers": [], "composite": None},
            garm_img=handle_file(garment_path),
            garment_des="test",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )
        print("Success!")
        break
    except Exception as e:
        print("Error:", e)
