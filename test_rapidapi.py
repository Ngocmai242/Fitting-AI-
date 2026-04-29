import os
import requests
import uuid

def test_rapidapi():
    api_key = "41bc05ce03msh67626f796ce6555p1c4872jsn5c4fa2d8cedd"
    url = "https://try-on-diffusion.p.rapidapi.com/try-on-file"
    person = os.path.abspath("backend/test_person.jpg")
    garment = os.path.abspath("backend/test_garment.jpg")
    
    files = {
        'avatar_image': ('avatar.png', open(person, 'rb'), 'image/png'),
        'clothing_image': ('garment.png', open(garment, 'rb'), 'image/png'),
    }
    payload = {
        'avatar_sex': 'female',
        'clothing_type': 'upper_body'
    }
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "try-on-diffusion.p.rapidapi.com"
    }
    print("Testing RapidAPI...")
    response = requests.post(url, files=files, data=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Type: {response.headers.get('Content-Type')}")
    if response.status_code == 200:
        print(f"Success! Preview: {response.text[:200]}")
    else:
        print(f"Error: {response.text[:200]}")

if __name__ == "__main__":
    test_rapidapi()
