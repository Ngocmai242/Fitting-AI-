import asyncio
import json
from playwright.async_api import async_playwright
import os

URL = "https://shopee.vn/legendary_official" 

async def debug_crawl():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        page = await context.new_page()
        print(f"Navigating to {URL}...")
        try:
            await page.goto(URL, timeout=60000, wait_until='networkidle')
            print(f"Page Title: {await page.title()}")
            
            # Dump HTML
            content = await page.content()
            with open("debug_shopee.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Dumped HTML to debug_shopee.html")
            
            # Check for products
            items = await page.locator("div.shop-search-result-view__item").count()
            print(f"Found {items} shop items via .shop-search-result-view__item")
            
            items2 = await page.locator("a[href*='sp_atk']").count()
            print(f"Found {items2} items via generic link search")

        except Exception as e:
            print(f"Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_crawl())
