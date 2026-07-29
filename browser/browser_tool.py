import os
import sys
from playwright.async_api import async_playwright

import asyncio
import tempfile

IS_HEADLESS = os.getenv("HEADLESS", "true" if sys.platform != "win32" else "false").lower() in ["true", "1", "yes"]
EXTRA_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]

browser_lock = asyncio.Lock()

def get_launch_kwargs():
    profile_dir = os.path.abspath("playwright_profile") if sys.platform == "win32" else os.path.join(tempfile.gettempdir(), "playwright_profile")
    kwargs = {
        "user_data_dir": profile_dir,
        "headless": IS_HEADLESS,
        "args": EXTRA_ARGS
    }
    # Check for system installed chromium on Linux / Streamlit Cloud
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(path):
            kwargs["executable_path"] = path
            break
    return kwargs


async def get_page_title(url: str):
    async with browser_lock:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch_persistent_context(**get_launch_kwargs())
            except Exception:
                await asyncio.sleep(1)
                browser = await p.chromium.launch_persistent_context(**get_launch_kwargs())
            page = browser.pages[0] if browser.pages else await browser.new_page()
            await page.goto(url)
            title = await page.title()
            await browser.close()
            return title

async def get_page_text(url: str, scrolls: int = 5):
    async with browser_lock:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch_persistent_context(**get_launch_kwargs())
            except Exception:
                await asyncio.sleep(1)
                browser = await p.chromium.launch_persistent_context(**get_launch_kwargs())
            page = browser.pages[0] if browser.pages else await browser.new_page()
            await page.goto(url)
            
            # Wait for React to mount
            await page.wait_for_timeout(3000)
            
            current_url = page.url.lower()
            page_title_str = await page.title()
            
            # Only trigger auth required if redirected to an explicit login URL or login title
            if "login" in current_url or "signup" in current_url or "checkpoint" in current_url or page_title_str in ["LinkedIn: Log In or Sign Up", "Sign In | LinkedIn"]:
                if not IS_HEADLESS:
                    print("\n*** ACTION REQUIRED: Please log in to LinkedIn in the opened browser window! You have 30 seconds. ***\n")
                    try:
                        await page.wait_for_timeout(30000)
                        current_url = page.url.lower()
                        page_title_str = await page.title()
                    except Exception:
                        pass

            if "login" in current_url or "signup" in current_url or "checkpoint" in current_url or page_title_str in ["LinkedIn: Log In or Sign Up", "Sign In | LinkedIn"]:
                await browser.close()
                return "AUTH_REQUIRED: This page requires logging into LinkedIn to access private content."

            # Focus and scroll to load feed items
            await page.mouse.click(500, 500)
            for _ in range(scrolls):
                await page.mouse.wheel(0, 4000)
                await page.wait_for_timeout(2000)

            try:
                await page.wait_for_selector("main", timeout=5000)
                text = await page.locator("main").inner_text()
            except Exception:
                text = await page.locator("body").inner_text()

            await browser.close()
            return text



async def screenshot(url):
    async with browser_lock:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch_persistent_context(**get_launch_kwargs())
            except Exception:
                await asyncio.sleep(1)
                browser = await p.chromium.launch_persistent_context(**get_launch_kwargs())
            page = browser.pages[0] if browser.pages else await browser.new_page()
            await page.goto(url)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="page.png")
            await browser.close()
            return "Screenshot saved."

