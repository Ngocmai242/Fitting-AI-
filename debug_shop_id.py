
import asyncio
from playwright.async_api import async_playwright
import json
import re

async def debug_shop_id():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--start-maximized']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://shopee.vn/coolmate.vn"
        print(f"Navigating to {url}...")
        
        await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        
        # Method 1: Regex on HTML
        content = await page.content()
        shop_id_match = re.search(r'"shopId":(\d+)', content)
        if shop_id_match:
            print(f"Found shopId via Regex: {shop_id_match.group(1)}")
            shop_id = shop_id_match.group(1)
            
            # Try to fetch items
            print(f"Attempting API fetch for items using shopId {shop_id}...")
            api_url = f"https://shopee.vn/api/v4/shop/search_items?limit=30&offset=0&shopid={shop_id}"
            
            data = await page.evaluate(f'''async () => {{
                try {{
                    const res = await fetch("{api_url}");
                    return await res.json();
                }} catch (e) {{ return {{ error: e.toString() }}; }}
            }}''')
            
            print("API Response Preview:")
            print(str(data)[:500])
            
            if 'items' in data:
                print(f"✅ Successfully fetched {len(data['items'])} items!")
                # Check first item for category info
                if len(data['items']) > 0:
                    first = data['items'][0]
                    print("First Item Sample:")
                    print(json.dumps(first.get('item_basic', {}), indent=2))
        else:
            print("Could not find shopId in HTML.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_shop_id())
