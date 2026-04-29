from gradio_client import Client, handle_file
import os

person_path = "c:/Mai/4/backend/test_p.png"
garment_path = "c:/Mai/4/backend/test_g.png"

# List of potential IDM-VTON spaces
spaces = [
    "yisol/IDM-VTON",
    "freddyaboulton/IDM-VTON",
    "adi1516/IDM_VTON",
    "fashn-ai/FASHN-TryOn",
    "levihsu/OOTDiffusion"
]

for s in spaces:
    print(f"Testing {s}...")
    try:
        client = Client(s)
        # Check if it has the /tryon endpoint
        endpoints = [e for e in client.endpoints if e[0] == "/tryon"]
        if endpoints:
            print(f"Found /tryon in {s}")
            # Try a very small prediction
            # ... actually just connecting is a good sign
    except Exception as e:
        print(f"Failed {s}: {e}")
