
import asyncio
from playwright.async_api import async_playwright
import json

async def intercept_shopee():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigate to shop...")
        
        # storage to capture responses
        captured_data = []

        async def handle_response(response):
            if "api/v4/shop/search_items" in response.url or "api/v4/shop/get_categories" in response.url:
                print(f"Captured API: {response.url}")
                try:
                    data = await response.json()
                    captured_data.append({
                        "url": response.url,
                        "data": data
                    })
                except:
                    pass

        page.on("response", handle_response)
        
        # Go to a shop page's "All Products" section
        await page.goto("https://shopee.vn/coolmate.vn/list", timeout=60000)
        await page.wait_for_timeout(5000) # Wait for network
        
        await browser.close()
        
        # Dump captured data to inspect
        with open("shopee_api_dump.json", "w", encoding="utf-8") as f:
            json.dump(captured_data, f, ensure_ascii=False, indent=2)
            
        print("Dumped API data to shopee_api_dump.json")

if __name__ == "__main__":
    asyncio.run(intercept_shopee())
