import asyncio
from playwright.async_api import async_playwright

async def login():
    print("Starting Playwright...")
    async with async_playwright() as p:
        # Launch using the exact same persistent context directory
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="playwright_profile", 
            headless=False
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        print("Navigating to LinkedIn...")
        await page.goto("https://www.linkedin.com/login")
        
        print("\n*** ACTION REQUIRED ***")
        print("A browser window has opened. Please manually log in to your LinkedIn account.")
        print("Once you are successfully logged in and see your feed, you can close this terminal window (Ctrl+C).")
        print("Your session will be automatically saved in the 'playwright_profile' folder for the AI agent to use!")
        
        # Keep the browser open for 300 seconds so you have plenty of time to log in
        await page.wait_for_timeout(300000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(login())
