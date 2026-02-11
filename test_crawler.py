import sys
sys.path.insert(0, 'g:\\1')

from data_engine.crawler.shopee import crawl_shop_url

url = "https://shopee.vn/-K%C3%88M-M%C3%9AT-NG%E1%BB%B0C-%C3%A1o-hai-d%C3%A2y-n%E1%BB%AF-tr%C6%A1n-basic-nhi%E1%BB%81u-m%C3%A0u-ch%E1%BA%A5t-thun-g%C3%A2n-m%C3%A1t-m%E1%BA%BB-sexy-c%C3%A1-t%C3%ADnh-%C3%A1o-2-d%C3%A2y-m%E1%BA%B7c-nh%C3%A0-n%E1%BB%AF-t%C3%ADnh-A543-SUTANO-i.184210921.28850598857"

try:
    products = crawl_shop_url(url, 5)
    print(f"\n\nTotal products: {len(products)}")
    if products:
        import json
        print(json.dumps(products[0], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
