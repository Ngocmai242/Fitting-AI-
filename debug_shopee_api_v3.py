
import requests
import json
import re

def get_shop_data(username="coolmate.vn"):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # 1. Resolve Shop ID
    try:
        url = f"https://shopee.vn/api/v4/shop/get_shop_detail?username={username}"
        print(f"Fetching Shop Detail: {url}")
        resp = requests.get(url, headers=headers)
        data = resp.json()
        
        if 'data' not in data:
            print("Failed to get shop details.")
            return

        shopid = data['data']['shopid']
        name = data['data']['name']
        print(f"✅ Found Shop ID: {shopid} (Name: {name})")
        
        # 2. Fetch Items
        items_url = f"https://shopee.vn/api/v4/shop/search_items?offset=0&limit=30&order=desc&sort_by=pop&shopid={shopid}"
        print(f"Fetching Items: {items_url}")
        items_resp = requests.get(items_url, headers=headers)
        items_data = items_resp.json()
        
        if 'items' in items_data:
            print(f"✅ Found {len(items_data['items'])} items.")
            # Print sample item to see category info
            if len(items_data['items']) > 0:
                first = items_data['items'][0]['item_basic']
                print("\nSample Item Data:")
                print(f"Name: {first.get('name')}")
                print(f"CatID: {first.get('catid')}")
                
                # Check if we can resolve category name via another API
                # api/v4/item/get?itemid={itemid}&shopid={shopid} might have full details including category structure
                itemid = first.get('itemid')
                detail_url = f"https://shopee.vn/api/v4/item/get?itemid={itemid}&shopid={shopid}"
                print(f"\nFetching Item Detail: {detail_url}")
                detail_resp = requests.get(detail_url, headers=headers)
                detail_json = detail_resp.json()
                
                if 'data' in detail_json:
                    cats = detail_json['data'].get('categories', [])
                    print("Categories found in item detail:")
                    for c in cats:
                        print(f"- {c.get('display_name')} (ID: {c.get('catid')})")
        else:
            print("No items found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_shop_data()
