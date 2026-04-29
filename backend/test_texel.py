import requests
import os
person_path = "c:/Mai/4/backend/test_p.png"
garment_path = "c:/Mai/4/backend/test_g.png"

url = "https://try-on-diffusion.p.rapidapi.com/try-on-file"
api_key = os.getenv("RAPIDAPI_KEY", "41bc05ce03msh67626f796ce6555p1c4872jsn5c4fa2d8cedd")

files = {
    'avatar_image': ('avatar.png', open(person_path, 'rb'), 'image/png'),
    'clothing_image': ('garment.png', open(garment_path, 'rb'), 'image/png'),
}
payload = {
    'avatar_sex': 'female',
    'clothing_type': 'upper_body'
}
headers = {
    "x-rapidapi-key": api_key,
    "x-rapidapi-host": "try-on-diffusion.p.rapidapi.com"
}
try:
    print("Calling API...")
    res = requests.post(url, files=files, data=payload, headers=headers)
    print(res.status_code)
    print(res.text[:500])
except Exception as e:
    print(e)
