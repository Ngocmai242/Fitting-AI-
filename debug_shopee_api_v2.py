
import asyncio
from playwright.async_api import async_playwright
import json

async def intercept_shopee():
    async with async_playwright() as p:
        # Launch with specific args to be less bot-like
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--start-maximized']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Navigate to shop...")
        
        captured_urls = []
        captured_json = []

        async def handle_response(response):
            # Capture any API-like response
            if "api/" in response.url or ".json" in response.url:
                captured_urls.append(response.url)
                
                # Try to get JSON body for likely candidates
                if "search_items" in response.url or "category" in response.url or "get_items" in response.url:
                    try:
                        data = await response.json()
                        captured_json.append({
                            "url": response.url,
                            "data_preview": str(data)[:200] # Preview only to save space
                        })
                    except: pass

        page.on("response", handle_response)
        
        # Go to a specific shop page
        await page.goto("https://shopee.vn/coolmate.vn", timeout=60000)
        
        # Human-like scroll
        print("Scrolling...")
        for _ in range(3):
            await page.mouse.wheel(0, 500)
            await page.wait_for_timeout(2000)
            
        await browser.close()
        
        print("\n=== Captured API URLs ===")
        for u in captured_urls:
            print(u)
            
        print(f"\nCaptured {len(captured_json)} JSON bodies.")

if __name__ == "__main__":
    asyncio.run(intercept_shopee())
