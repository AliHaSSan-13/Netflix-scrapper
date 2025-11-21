import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import random
from .logger import logger

class BrowserManager:
    def __init__(self, human_simulator):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.human_simulator = human_simulator

    async def setup(self):
        """Initialize browser and page with human-like behavior"""
        logger.info("🚀 Launching browser...")
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.firefox.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--no-default-browser_check',
                ]
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1200, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True, 
            )
            
            await self.context.route("**/*.{png,jpg,jpeg,webp,svg}", lambda route: route.abort())
            
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            self.page = await self.context.new_page()
            logger.info("✅ Browser launched successfully.")
            return self.page, self.context
        except Exception as e:
            logger.error(f"❌ Failed to launch browser or set up context: {e}")
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            raise

    async def close(self):
        """Close browser and playwright"""
        logger.info("👋 Closing browser...")
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("✅ Browser closed successfully.")
        except Exception as e:
            logger.error(f"❌ Error while closing browser: {e}")

    async def set_cookies(self):
        """
        Load cookies from cookies.json if available, otherwise use static ones.
        Applies them to the Playwright browser context.
        """
        cookies_file = "cookies.json"
        cookies = []

        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)
                logger.info("🍪 Loaded existing cookies from cookies.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load cookies.json, falling back to static: {e}")

        if not cookies:
            logger.info("⚠️ Using static cookies (first-time run)")
            cookies = [
                {
                    "name": "user_token",
                    "value": "29bb845a66aa3ea49b7e0e3978c94512",
                    "domain": ".net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstCfa1190725",
                    "value": "1760801564793",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstCla1190725",
                    "value": "1760801564793",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstCmu1190725",
                    "value": "1760801564793",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstPn1190725",
                    "value": "1",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstPt1190725",
                    "value": "1",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstCnv1190725",
                    "value": "1",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "HstCns1190725",
                    "value": "1",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "c_ref_1190725",
                    "value": "https%3A%2F%2Faccounts.google.com%2F",
                    "domain": "net20.cc",
                    "path": "/",
                },
                {
                    "name": "t_hash",
                    "value": "8e45cb69b2b4ec3d15802de127c7a1c5%3A%3A1762255784%3A%3Akp",
                    "domain": ".net20.cc",
                    "path": "/",
                },
                {
                    "name": "lang",
                    "value": "eng",
                    "domain": ".net20.cc",
                    "path": "/",
                },
                {
                    "name": "SE80189685",
                    "value": "80189599",
                    "domain": ".net20.cc",
                    "path": "/",
                },
                {
                    "name": "recentplay",
                    "value": "SE80189685",
                    "domain": ".net20.cc",
                    "path": "/",
                },
                {
                    "name": "80189599",
                    "value": "121%3A3701",
                    "domain": ".net20.cc",
                    "path": "/",
                },
                {
                    "name": "t_hash_t",
                    "value": "6b09754460360143b4d1c04f90b09dff%3A%3A06e18f5529835bab2ebbd9cebae0c186%3A%3A1762185938%3A%3Akp",
                    "domain": ".net20.cc",
                    "path": "/",
                },
            ]

        try:
            await self.context.add_cookies(cookies)
            logger.info("✅ Cookies applied to browser context!")
        except Exception as e:
            logger.error(f"❌ Error applying cookies to browser context: {e}")
            raise

    async def save_fresh_cookies(self):
        """
        Save current browser cookies to cookies.json after login.
        """
        try:
            cookies = await self.context.cookies()
            with open("cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            logger.info("💾 Fresh cookies saved to cookies.json")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save fresh cookies: {e}")

    async def handle_verification_page(self):
        """Handle the verification page with more human-like behavior"""
        logger.info("🛡️ Verification page detected... simulating human behavior...")

        try:
            await self.human_simulator.async_random_delay(2500, 5500)

            for _ in range(random.randint(2, 4)):
                start_x, start_y = random.randint(100, 800), random.randint(100, 600)
                end_x, end_y = random.randint(300, 1000), random.randint(200, 700)
                path = self.human_simulator.mouse_movement_pattern(start_x, start_y, end_x, end_y)
                for (x, y) in path:
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.02, 0.08))
                await self.human_simulator.async_random_delay(500, 1500)

            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(200, 800)
                direction = random.choice([1, -1])
                await self.page.mouse.wheel(0, scroll_amount * direction)
                await self.human_simulator.async_random_delay(700, 1500)

            recaptcha_iframe = None
            iframe_selectors = [
                'iframe[title*="reCAPTCHA"]',
                'iframe[src*="google.com/recaptcha"]',
            ]

            for iframe_selector in iframe_selectors:
                frame_el = await self.page.query_selector(iframe_selector)
                if frame_el:
                    recaptcha_iframe = frame_el
                    logger.info(f"🔍 Found reCAPTCHA iframe: {iframe_selector}")
                    break

            if recaptcha_iframe:
                frame = await recaptcha_iframe.content_frame()
                if not frame:
                    logger.warning("⚠️ Could not access reCAPTCHA frame")
                    return False

                await self.human_simulator.async_random_delay(2500, 4500)

                checkbox_selectors = ['.recaptcha-checkbox-border', '.recaptcha-checkbox', 'div[role="checkbox"]']
                for selector in checkbox_selectors:
                    checkbox = await frame.query_selector(selector)
                    if checkbox:
                        box = await checkbox.bounding_box()
                        if box:
                            await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=random.randint(10, 20))
                            await self.human_simulator.async_random_delay(500, 1200)
                            await checkbox.click()
                            logger.info("✅ Clicked reCAPTCHA checkbox (human-style)")
                            break

            logger.info("⏳ Waiting for verification result...")
            for i in range(12):
                current_url = self.page.url
                if "verify" not in current_url:
                    logger.info("✅ Verification passed — human behavior succeeded!")
                    return True
                await self.human_simulator.async_random_delay(2000, 3500)
                await self.page.mouse.wheel(0, random.randint(100, 400))

            logger.warning("❌ Still on verification page after multiple tries.")
            return False

        except Exception as e:
            logger.error(f"❌ Error during verification handling: {e}")
            return False

    async def navigate_to_home(self):
        """Navigate to the home page"""
        logger.info("🧭 Navigating to https://net20.cc/home...")
        
        try:
            await self.page.goto("https://net20.cc/home", wait_until="domcontentloaded", timeout=45000) 
            await self.human_simulator.async_random_delay(2000, 5000)
            
            current_url = self.page.url
            if "verify" in current_url:
                logger.info("🔄 Redirected to verification page...")
                success = await self.handle_verification_page()
                if success:
                    await self.human_simulator.async_random_delay(1500, 3500)
                    await self.page.goto("https://net20.cc/home", wait_until="domcontentloaded", timeout=45000)
                    await self.human_simulator.async_random_delay(2000, 4000)
                else:
                    logger.error("❌ Could not bypass verification.")
                    return False
            
            await self.page.wait_for_selector('.searchTab', timeout=15000)
            logger.info("✅ Successfully authenticated!")
            await self.save_fresh_cookies()
            return True
        except PlaywrightTimeoutError:
            logger.error("❌ Timeout while navigating to home or waiting for searchTab. Authentication failed.")
            return False
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during navigation or authentication: {e}")
            return False
