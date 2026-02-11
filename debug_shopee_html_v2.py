
import asyncio
from playwright.async_api import async_playwright

async def debug_shopee_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://shopee.vn/coolmate.vn", timeout=60000, wait_until='networkidle')
        
        # Scroll more aggressively
        for _ in range(5):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1)
        
        # Try finding ANY anchor tags
        anchors = await page.locator("a").count()
        print(f"Total anchors: {anchors}")
        
        # Try finding product cards by class (often used)
        cards = await page.locator(".shop-search-result-view__item").count()
        print(f"Cards via .shop-search-result-view__item: {cards}")
        
        # Try the link pattern again
        items = await page.locator("a[href*='-i.']").count()
        print(f"Items via href pattern: {items}")
        
        if items > 0:
            first_item = page.locator("a[href*='-i.']").first
            html = await first_item.evaluate("el => el.outerHTML")
            print("\nFirst Item HTML:")
            print(html[:2000])
        else:
            # Dump body to see what's there (truncated)
            body = await page.content()
            print("\nPage Content Preview:")
            print(body[:2000])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_shopee_html())
