import requests

url = "https://huggingface.co/api/spaces?search=vton"
res = requests.get(url).json()

spaces = [s['id'] for s in res if s.get('id')]
print(f"Found {len(spaces)} spaces")
for s in spaces[:10]:
    print(s)
