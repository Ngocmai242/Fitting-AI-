
import asyncio
from playwright.async_api import async_playwright

async def debug_shopee_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://shopee.vn/coolmate.vn", timeout=60000)
        
        # Scroll a bit
        await page.evaluate("window.scrollTo(0, 1000)")
        await asyncio.sleep(2)
        
        # Get first few items
        items = await page.locator("a[href*='-i.']").all()
        print(f"Found {len(items)} items")
        
        for i, item in enumerate(items[:3]):
            print(f"\n--- Item {i} ---")
            outer_html = await item.evaluate("el => el.outerHTML")
            print(outer_html[:1000]) # Print first 1000 chars
            
            # Try to find image
            img = item.locator("img").first
            if await img.count() > 0:
                src = await img.get_attribute("src")
                print(f"Image Src: {src}")
            else:
                print("No img tag found inside anchor")
                
            # Try to find price text
            text = await item.inner_text()
            print(f"Inner Text: {text!r}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_shopee_html())
