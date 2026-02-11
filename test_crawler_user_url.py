
from data_engine.crawler.shopee import crawl_shop_url
import json

url = "https://shopee.vn/sutano.vn?categoryId=100017&entryPoint=ShopByPDP&itemId=28850598857"
print(f"Testing URL: {url}")
try:
    results = crawl_shop_url(url, limit=5)
    print(f"Found {len(results)} products.")
    if len(results) > 0:
        print(json.dumps(results[0], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
