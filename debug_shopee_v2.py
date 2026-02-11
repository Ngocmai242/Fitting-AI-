import logging
import time
import json
import re
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL = "https://shopee.vn/sutano.vn?categoryId=100017&entryPoint=ShopByPDP&itemId=6012227940"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        # Stealth
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        
        # Intercept responses
        api_responses = []
        def handle_response(response):
            if "search_items" in response.url and response.status == 200:
                try:
                    data = response.json()
                    logger.info(f"Intercepted search_items: {len(data.get('items', []))} items")
                    api_responses.append(data)
                except:
                    pass
        
        page.on("response", handle_response)
        
        logger.info(f"Navigating to {URL}")
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            logger.error(f"Navigation error: {e}")

        page.screenshot(path="debug_page_load.png")
        logger.info(f"Page title: {page.title()}")
        
        # Scroll to trigger APIs
        for _ in range(3):
            page.mouse.wheel(0, 1000)
            time.sleep(1)
            
        # Try to find shopid from content
        content = page.content()
        shopid = None
        match = re.search(r'"shopid":\s*(\d+)', content)
        if match:
            shopid = match.group(1)
            logger.info(f"Found shopid in regex: {shopid}")
            
        if shopid:
            # Try calling API explicitly using the SEARCH endpoint user suggested
            # https://shopee.vn/api/v4/search/search_items?by=relevancy&limit=30&match_id=...&newest=0&order=desc&page_type=shop&scenario=PAGE_SHOP_SEARCH&version=2
            api_url = f"https://shopee.vn/api/v4/search/search_items?by=relevancy&limit=50&match_id={shopid}&newest=0&order=desc&page_type=shop&scenario=PAGE_SHOP_SEARCH&version=2"
            logger.info(f"Fetching manually from: {api_url}")
            
            res = page.evaluate(f"""
                async () => {{
                    try {{
                        const r = await fetch('{api_url}');
                        return await r.json();
                    }} catch(e) {{
                        return {{error: e.toString()}};
                    }}
                }}
            """)
            
            if 'items' in res:
                logger.info(f"Manual Fetch Success: {len(res['items'])} items")
            else:
                logger.error(f"Manual Fetch Failed: {res.keys()}")

        browser.close()

if __name__ == "__main__":
    run()
