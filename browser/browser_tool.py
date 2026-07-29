import os
from playwright.async_api import async_playwright

IS_HEADLESS = os.getenv("HEADLESS", "false").lower() in ["true", "1", "yes"]
EXTRA_ARGS = ["--no-sandbox", "--disable-setuid-sandbox"]

async def get_page_title(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_profile",
            headless=IS_HEADLESS,
            args=EXTRA_ARGS
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(url)
        title = await page.title()
        await browser.close()
        return title

async def get_page_text(url: str, scrolls: int = 5):
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_profile",
            headless=IS_HEADLESS,
            args=EXTRA_ARGS
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(url)
        
        # Wait for user to log in if they hit the auth wall
        if not IS_HEADLESS and ("Sign In" in await page.title() or "LinkedIn Login" in await page.title() or ("Feed" not in await page.title() and "LinkedIn" in await page.title())):
            print("\n*** ACTION REQUIRED: Please log in to LinkedIn in the opened browser window! You have 60 seconds. ***\n")
            try:
                await page.wait_for_timeout(30000) # Give 30s to log in manually the first time
            except:
                pass
                
        # wait a bit for React to mount and load data
        await page.wait_for_timeout(4000)
        
        # Click on the center of the page to ensure it's in focus
        await page.mouse.click(500, 500)
        
        # Scroll down multiple times using mouse wheel (much more reliable than JS scrolling)
        for _ in range(scrolls):
            await page.mouse.wheel(0, 4000) # Scroll down aggressively
            await page.wait_for_timeout(2000)
        
        try:
            # Try to grab the main profile container first
            await page.wait_for_selector("main", timeout=5000)
            text = await page.locator("main").inner_text()
        except:
            # Fallback to body
            text = await page.locator("body").inner_text()
            
        await browser.close()
        return text

async def screenshot(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_profile",
            headless=IS_HEADLESS,
            args=EXTRA_ARGS
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)
        await page.screenshot(path="page.png")
        await browser.close()
        return "Screenshot saved."