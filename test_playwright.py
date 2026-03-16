from playwright.sync_api import sync_playwright

def test_playwright():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            print("Successfully launched chromium!")
            browser.close()
    except Exception as e:
        print(f"Failed to launch chromium: {e}")

if __name__ == "__main__":
    test_playwright()
