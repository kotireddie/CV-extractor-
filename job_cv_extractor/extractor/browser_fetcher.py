"""
Browser-based Content Fetcher Module

Uses Playwright for headless browser rendering to fetch content from
JavaScript-dependent pages (Apple, iCIMS, etc.).
"""

import sys
import os
from typing import Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger

# Try to import Playwright
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not available. Install with: pip install playwright && playwright install chromium")


@dataclass
class BrowserFetchResult:
    """Result of a browser-based fetch operation."""
    success: bool
    html: Optional[str]
    error_message: Optional[str]
    final_url: str
    method: str = "browser"


def is_browser_available() -> bool:
    """Check if browser-based fetching is available."""
    return PLAYWRIGHT_AVAILABLE


def fetch_with_browser(
    url: str, 
    timeout: int = 30000,
    wait_for_selector: Optional[str] = None,
    wait_for_load_state: str = "networkidle"
) -> BrowserFetchResult:
    """
    Fetch page content using a headless browser.
    
    This renders JavaScript and waits for dynamic content to load.
    
    Args:
        url: URL to fetch
        timeout: Timeout in milliseconds
        wait_for_selector: Optional CSS selector to wait for
        wait_for_load_state: Load state to wait for ('load', 'domcontentloaded', 'networkidle')
    
    Returns:
        BrowserFetchResult containing rendered HTML or error information
    """
    if not PLAYWRIGHT_AVAILABLE:
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message="Playwright not installed. Install with: pip install playwright && playwright install chromium",
            final_url=url
        )
    
    logger.info(f"Fetching URL with browser: {url}")
    
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            # Create context with realistic viewport and user agent
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
            )
            
            page = context.new_page()
            
            # Navigate to URL
            logger.debug(f"Navigating to: {url}")
            response = page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            
            if not response:
                browser.close()
                return BrowserFetchResult(
                    success=False,
                    html=None,
                    error_message="Failed to get response from page",
                    final_url=url
                )
            
            # Check response status
            if response.status >= 400:
                browser.close()
                return BrowserFetchResult(
                    success=False,
                    html=None,
                    error_message=f"HTTP {response.status}",
                    final_url=page.url
                )
            
            # Wait for page to fully load
            logger.debug(f"Waiting for load state: {wait_for_load_state}")
            try:
                page.wait_for_load_state(wait_for_load_state, timeout=timeout)
            except PlaywrightTimeout:
                logger.warning(f"Timeout waiting for {wait_for_load_state}, continuing anyway")
            
            # Wait for specific selector if provided
            if wait_for_selector:
                logger.debug(f"Waiting for selector: {wait_for_selector}")
                try:
                    page.wait_for_selector(wait_for_selector, timeout=timeout // 2)
                except PlaywrightTimeout:
                    logger.warning(f"Timeout waiting for selector {wait_for_selector}")
            
            # Additional wait for dynamic content
            # Many SPAs need a bit more time to fully render
            page.wait_for_timeout(2000)  # 2 second buffer
            
            # Get the rendered HTML
            html_content = page.content()
            final_url = page.url
            
            logger.info(f"Successfully fetched {len(html_content)} characters via browser")
            
            browser.close()
            
            return BrowserFetchResult(
                success=True,
                html=html_content,
                error_message=None,
                final_url=final_url
            )
    
    except PlaywrightTimeout as e:
        error_msg = f"Browser timeout: {str(e)}"
        logger.error(error_msg)
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message=error_msg,
            final_url=url
        )
    
    except Exception as e:
        error_msg = f"Browser fetch error: {str(e)}"
        logger.error(error_msg)
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message=error_msg,
            final_url=url
        )


def fetch_apple_jobs(url: str) -> BrowserFetchResult:
    """
    Specialized fetcher for Apple job pages.
    
    Apple jobs pages load content dynamically via JavaScript/React
    and need specific handling to wait for the job description to render.
    
    Args:
        url: Apple jobs URL
    
    Returns:
        BrowserFetchResult with rendered HTML
    """
    if not PLAYWRIGHT_AVAILABLE:
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message="Playwright not installed",
            final_url=url
        )
    
    logger.info(f"Fetching Apple Jobs URL with browser: {url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
            )
            
            page = context.new_page()
            
            # Navigate to Apple Jobs
            response = page.goto(url, timeout=60000, wait_until='domcontentloaded')
            
            if not response or response.status >= 400:
                browser.close()
                return BrowserFetchResult(
                    success=False,
                    html=None,
                    error_message=f"HTTP {response.status if response else 'No response'}",
                    final_url=url
                )
            
            # Wait for React app to initialize
            try:
                page.wait_for_load_state('networkidle', timeout=30000)
            except PlaywrightTimeout:
                logger.warning("Apple networkidle timeout, continuing")
            
            # Apple Jobs specific: wait for job content to appear
            # Try multiple selectors that Apple might use
            selectors_to_try = [
                '[data-testid="job-details"]',
                '.job-details',
                '[class*="JobDescription"]',
                '[class*="job-description"]',
                '#job-details',
                'section[class*="posting"]',
                'div[class*="details"]',
                'main',
            ]
            
            found_content = False
            for selector in selectors_to_try:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    logger.debug(f"Found Apple content with selector: {selector}")
                    found_content = True
                    break
                except PlaywrightTimeout:
                    continue
            
            # Extra wait for React content to fully render
            page.wait_for_timeout(5000)  # 5 second buffer
            
            # Scroll to load any lazy content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            
            # Try to extract just the job content instead of full page
            # This avoids the content cleaner stripping out job details
            job_content_selectors = [
                '#jobdetails-wrapper',
                '[id*="jobdetails"]',
                'main',
                '[class*="job-details"]',
                'article',
            ]
            
            extracted_content = None
            for selector in job_content_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        content = element.inner_html()
                        # Only use if it has substantial content
                        if len(content) > 500:
                            extracted_content = f"<div id='job-content'>{content}</div>"
                            logger.info(f"Apple: Extracted {len(content)} chars from {selector}")
                            break
                except Exception as e:
                    logger.debug(f"Apple selector {selector} failed: {e}")
                    continue
            
            # Fall back to full page if no job content found
            if extracted_content:
                html_content = extracted_content
            else:
                html_content = page.content()
            
            final_url = page.url
            
            logger.info(f"Apple Jobs fetched {len(html_content)} characters")
            browser.close()
            
            return BrowserFetchResult(
                success=True,
                html=html_content,
                error_message=None,
                final_url=final_url
            )
            
    except Exception as e:
        error_msg = f"Apple browser fetch error: {str(e)}"
        logger.error(error_msg)
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message=error_msg,
            final_url=url
        )


def fetch_icims_jobs(url: str) -> BrowserFetchResult:
    """
    Specialized fetcher for iCIMS job pages.
    
    iCIMS uses a complex SPA that requires JavaScript rendering.
    The job content is often loaded in an iframe or via AJAX after initial page load.
    
    Args:
        url: iCIMS jobs URL
    
    Returns:
        BrowserFetchResult with rendered HTML
    """
    if not PLAYWRIGHT_AVAILABLE:
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message="Playwright not installed",
            final_url=url
        )
    
    logger.info(f"Fetching iCIMS URL with browser: {url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            
            page = context.new_page()
            
            # Navigate with longer timeout for iCIMS
            response = page.goto(url, timeout=60000, wait_until='domcontentloaded')
            
            if not response or response.status >= 400:
                browser.close()
                return BrowserFetchResult(
                    success=False,
                    html=None,
                    error_message=f"HTTP {response.status if response else 'No response'}",
                    final_url=url
                )
            
            # Wait for page to load
            try:
                page.wait_for_load_state('networkidle', timeout=30000)
            except PlaywrightTimeout:
                logger.warning("iCIMS networkidle timeout, continuing")
            
            # iCIMS often loads content in iframes - check for iframes
            frames = page.frames
            logger.debug(f"Found {len(frames)} frames")
            
            # Wait longer for dynamic content
            page.wait_for_timeout(5000)  # 5 second wait for AJAX
            
            # Try to find job content in various selectors
            selectors_to_try = [
                '[class*="iCIMS_JobContent"]',
                '[class*="job-description"]', 
                '[class*="jobDescription"]',
                '[data-testid*="job"]',
                '.iCIMS_MainWrapper',
                'main',
                'article',
            ]
            
            for selector in selectors_to_try:
                try:
                    element = page.query_selector(selector)
                    if element:
                        logger.debug(f"Found iCIMS content with selector: {selector}")
                        break
                except Exception:
                    pass
            
            # Get full page HTML
            html_content = page.content()
            
            # Also try to get content from iframes
            for frame in frames[1:]:  # Skip main frame
                try:
                    frame_html = frame.content()
                    if len(frame_html) > 1000 and ('job' in frame_html.lower() or 'description' in frame_html.lower()):
                        logger.debug("Found job content in iframe")
                        html_content = html_content + "\n" + frame_html
                except Exception:
                    pass
            
            logger.info(f"iCIMS fetched {len(html_content)} characters")
            browser.close()
            
            return BrowserFetchResult(
                success=True,
                html=html_content,
                error_message=None,
                final_url=page.url
            )
            
    except Exception as e:
        error_msg = f"iCIMS browser fetch error: {str(e)}"
        logger.error(error_msg)
        return BrowserFetchResult(
            success=False,
            html=None,
            error_message=error_msg,
            final_url=url
        )


def fetch_workday_jobs(url: str) -> BrowserFetchResult:
    """
    Specialized fetcher for Workday job pages.
    
    Workday uses a complex SPA architecture.
    
    Args:
        url: Workday jobs URL
    
    Returns:
        BrowserFetchResult with rendered HTML
    """
    return fetch_with_browser(
        url,
        timeout=45000,
        wait_for_selector='[data-automation-id="jobPostingDescription"], .job-description',
        wait_for_load_state='networkidle'
    )


def get_platform_fetcher(source: str):
    """
    Get the appropriate browser fetcher for a platform.
    
    Args:
        source: Platform source string
    
    Returns:
        Fetcher function for the platform
    """
    fetchers = {
        "apple": fetch_apple_jobs,
        "icims": fetch_icims_jobs,
        "workday": fetch_workday_jobs,
    }
    return fetchers.get(source, fetch_with_browser)
