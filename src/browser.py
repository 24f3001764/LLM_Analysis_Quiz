from playwright.async_api import async_playwright
from typing import Optional, Dict, Any
import asyncio
import logging
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages browser instances and provides methods for web scraping.
    Uses Playwright for headless browser automation.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    async def __aenter__(self):
        """Initialize the browser and context when entering the context manager."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-features=site-per-process',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create a new browser context
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            java_script_enabled=True,
            ignore_https_errors=True,
            bypass_csp=True
        )
        
        # Add stealth mode to avoid detection
        await self.context.add_init_script("""
        // Overwrite the `languages` property to use a custom getter.
        Object.defineProperty(navigator, 'languages', {
            get: function() {
                return ['en-US', 'en'];
            },
        });
        
        // Overwrite the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'plugins', {
            get: function() {
                // This just needs to have `length > 0`, but we could mock the plugins too
                return [1, 2, 3, 4, 5];
            },
        });
        
        // Overwrite the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'webdriver', {
            get: function () {
                return false;
            },
        });
        """)
        
        # Create a new page
        self.page = await self.context.new_page()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting the context manager."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def fetch_page(self, url: str, wait_for_selector: str = None, timeout: int = None) -> str:
        """
        Fetch a web page and return its content.
        
        Args:
            url: The URL to fetch
            wait_for_selector: Optional CSS selector to wait for before getting content
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            str: The page content as HTML
        """
        if timeout is None:
            timeout = settings.BROWSER_TIMEOUT * 1000  # Convert to milliseconds
            
        try:
            logger.info(f"Fetching URL: {url}")
            await self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            # Wait for the specified selector if provided
            if wait_for_selector:
                logger.debug(f"Waiting for selector: {wait_for_selector}")
                await self.page.wait_for_selector(wait_for_selector, timeout=timeout)
            
            # Get the page content
            content = await self.page.content()
            return content
            
        except Exception as e:
            logger.error(f"Error fetching page {url}: {str(e)}")
            raise
    
    async def extract_quiz_data(self, url: str) -> Dict[str, Any]:
        """
        Extract quiz data from a given URL.
        
        Args:
            url: The quiz URL
            
        Returns:
            Dict containing quiz data
        """
        try:
            # Fetch the quiz page
            content = await self.fetch_page(url, wait_selector="body")
            
            # TODO: Implement quiz data extraction logic
            # This will need to be customized based on the quiz format
            
            return {
                "url": url,
                "content": content[:500] + "..." if len(content) > 500 else content,  # Truncate for logging
                "questions": [],  # Will contain extracted questions
                "metadata": {}   # Additional metadata
            }
            
        except Exception as e:
            logger.error(f"Error extracting quiz data: {str(e)}")
            raise

# Example usage:
# async def example():
#     async with BrowserManager() as browser:
#         data = await browser.extract_quiz_data("https://example.com/quiz")
#         print(data)
# 
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(example())
