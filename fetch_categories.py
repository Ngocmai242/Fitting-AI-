
import requests
import json

def get_categories():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://shopee.vn/'
    }
    
    try:
        url = "https://shopee.vn/api/v4/pages/get_category_tree"
        print(f"Fetching {url}...")
        resp = requests.get(url, headers=headers)
        print(f"Status: {resp.status_code}")
        
        data = resp.json()
        
        # Save to file to inspect
        with open("shopee_categories.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("Saved category tree to shopee_categories.json")
        
        # Analyze top level
        cats = data.get('data', {}).get('category_list', [])
        print(f"Found {len(cats)} root categories.")
        
        for c in cats:
            print(f"- {c.get('display_name')} (ID: {c.get('catid')})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_categories()
