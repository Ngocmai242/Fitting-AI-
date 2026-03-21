import requests
import time
import uuid

# Start a VTON task
url = "http://127.0.0.1:8080/api/virtual-tryon"

# We must send a small test image to simulate upload
with open("test_img.jpg", "wb") as f:
    f.write(b"fake image data")

files = {'photo': ('test_img.jpg', open('test_img.jpg', 'rb'), 'image/jpeg')}
data = {
    'gender': 'female',
    'occasion': 'casual',
    'style': 'any',
    'body_shape': 'hourglass',
    'garment_type': 'tops',
    'budget': 'any'
}

print("Posting to /api/virtual-tryon...")
resp = requests.post(url, files=files, data=data)
print(resp.status_code, resp.text)
if resp.status_code == 202:
    j = resp.json()
    task_id = j['task_id']
    print("Got task ID:", task_id)
    
    for i in range(10):
        print(f"Polling {i+1}...")
        r = requests.get(f"http://127.0.0.1:8080/api/virtual-tryon/status/{task_id}")
        print(r.status_code, r.text)
        if "Task not found" in r.text or "completed" in r.text or "failed" in r.text:
            break
        time.sleep(2)
