import os
from gradio_client import Client, handle_file

print("Testing Fashn VTON 1.5 free API...")
try:
    client = Client("fashn-ai/fashn-vton-1.5")
    # Use dummy paths that exist, I'll create them or point to existing
    # Let's find any image file inside the frontend folder
    # Assuming tryon.html exists, maybe there's a favicon. Or just use a random image from internet
    
    import requests
    with open('t_person.jpg', 'wb') as f:
        f.write(requests.get('https://images.unsplash.com/photo-1517365830460-955ce3ccd263?w=500').content)
    with open('t_garm.jpg', 'wb') as f:
        f.write(requests.get('https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=500').content)

    print("Submitting predict...")
    res = client.predict(
        person_image=handle_file('t_person.jpg'),
        garment_image=handle_file('t_garm.jpg'),
        category="tops",
    )
    print("SUCCESS", res)
except Exception as e:
    print("FAILED FASHN:", type(e).__name__, str(e))

print("Testing IDM-VTON free API...")
try:
    client = Client("yisol/IDM-VTON")
    res = client.predict(
        dict={"background": handle_file('t_person.jpg'), "layers": [], "composite": None},
        garm_img=handle_file('t_garm.jpg'),
        garment_des="",
        is_checked=True,
        is_checked_crop=False,
        denoise_steps=30,
        seed=42,
    )
    print("SUCCESS", res)
except Exception as e:
    print("FAILED IDM:", type(e).__name__, str(e))
