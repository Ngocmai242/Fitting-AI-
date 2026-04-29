from gradio_client import Client, handle_file
import sys, os
person_path = "c:/Mai/4/backend/test_p.png"
garment_path = "c:/Mai/4/backend/test_g.png"
try:
    c = Client("levihsu/OOTDiffusion")
    res = c.predict(
        vton_img=handle_file(person_path),
        garm_img=handle_file(garment_path),
        category="Upper-body",
        n_samples=1,
        n_steps=20,
        image_scale=2.0,
        seed=-1,
        api_name="/process_dc"
    )
    print("Success:", res)
except Exception as e:
    print("Error:", e)
