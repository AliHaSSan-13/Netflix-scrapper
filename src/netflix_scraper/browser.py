import asyncio
from typing import Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import random
from .logger import logger
from .exceptions import BrowserSetupError, NetflixAuthError, NavigationError

class BrowserManager:
    def __init__(self, human_simulator, config=None):
        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.human_simulator = human_simulator
        self.config = config or {}
        self.browser_cfg = self.config.get("browser", {})
        self.selectors = self.config.get("selectors", {})
        self.timeouts = self.config.get("timeouts", {})
        self.app_cfg = self.config.get("app", {})
        self.site_cfg = self.config.get("site", {})

    async def setup(self, browser_type="chromium"):
        """Initialize browser and page with human-like behavior"""
        if browser_type == "chrome":
            browser_type = "chromium"

        logger.info(f"🚀 Launching {browser_type}...")
        try:
            self.playwright = await async_playwright().start()
            
            launcher = getattr(self.playwright, browser_type)
            self.browser = await launcher.launch(
                headless=self.browser_cfg.get("headless", True),
                args=self.browser_cfg.get(
                    "launch_args",
                    [
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--no-default-browser_check',
                    ],
                ),
            )
            
            self.context = await self.browser.new_context(
                viewport=self.browser_cfg.get("viewport", {'width': 1200, 'height': 800}),
                user_agent=self.browser_cfg.get(
                    "user_agent",
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ),
                ignore_https_errors=self.browser_cfg.get("ignore_https_errors", True),
            )
            
            await self.context.route(
                self.browser_cfg.get("block_resource_pattern", "**/*.{png,jpg,jpeg,webp,svg}"),
                lambda route: route.abort(),
            )
            
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            self.page = await self.context.new_page()
            logger.info("✅ Browser launched successfully.")
            return self.page, self.context
        except Exception as e:
            err_msg = str(e).lower()
            if "executable doesn't exist" in err_msg or "not installed" in err_msg:
                from .installer import install_playwright_browser
                logger.warning(f"⚠️ {browser_type} browser is missing.")
                if install_playwright_browser(browser_type):
                    # Clean up the failed playwright instance before retrying
                    if self.playwright:
                        await self.playwright.stop()
                    return await self.setup(browser_type)

            logger.error(f"❌ Failed to launch browser or set up context: {e}")
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            raise BrowserSetupError(f"Failed to initialize Playwright or Browser: {e}")

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
        """Load cookies from configured cookies file and apply to context."""
        path = self.app_cfg.get("cookies_file", "cookies.json")
        if not os.path.exists(path):
            logger.warning("⚠️ No cookies file found.")
            return

        try:
            with open(path, "r") as f:
                cookies = json.load(f)
            if not cookies:
                return
            await self.context.add_cookies(cookies)
            logger.info(f"✅ Applied cookies from {path}")
        except Exception as e:
            logger.error(f"❌ Error applying cookies: {e}")
            raise NetflixAuthError(f"Failed to apply cookies: {e}")

    async def save_fresh_cookies(self):
        """
        Save current browser cookies after login.
        """
        cookies_file = self.app_cfg.get("cookies_file", "cookies.json")
        try:
            cookies = await self.context.cookies()
            with open(cookies_file, "w") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"💾 Fresh cookies saved to {cookies_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save fresh cookies: {e}")

    async def handle_verification_page(self):
        """Handle the verification page with human-like behavior."""
        vcfg = self.browser_cfg.get("verification", {})
        logger.info("🛡️ Verification page detected... simulating human...")

        try:
            await self.human_simulator.async_random_delay(*vcfg.get("initial_delay_ms", [2500, 5500]))
            await self._simulate_mouse_movements(vcfg)
            await self._simulate_scrolling(vcfg)
            
            if await self._solve_recaptcha(vcfg):
                logger.info("✅ reCAPTCHA checkbox clicked.")

            logger.info("⏳ Waiting for verification result...")
            return await self._poll_verification_result(vcfg)
        except Exception as e:
            logger.error(f"❌ Error during verification: {e}")
            raise NetflixAuthError(f"Verification bypass failed: {e}")

    async def _simulate_mouse_movements(self, vcfg):
        moves = range(random.randint(*vcfg.get("mouse_moves_range", [2, 4])))
        for _ in moves:
            s_x, s_y = random.randint(*vcfg.get("mouse_start_x_range", [100, 800])), random.randint(*vcfg.get("mouse_start_y_range", [100, 600]))
            e_x, e_y = random.randint(*vcfg.get("mouse_end_x_range", [300, 1000])), random.randint(*vcfg.get("mouse_end_y_range", [200, 700]))
            path = self.human_simulator.mouse_movement_pattern(s_x, s_y, e_x, e_y)
            for (x, y) in path:
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(*vcfg.get("mouse_step_delay_s", [0.02, 0.08])))
            await self.human_simulator.async_random_delay(*vcfg.get("mouse_pause_delay_ms", [500, 1500]))

    async def _simulate_scrolling(self, vcfg):
        iters = range(random.randint(*vcfg.get("scroll_iterations_range", [2, 4])))
        for _ in iters:
            amt = random.randint(*vcfg.get("scroll_amount_range", [200, 800])) * random.choice([1, -1])
            await self.page.mouse.wheel(0, amt)
            await self.human_simulator.async_random_delay(*vcfg.get("scroll_pause_delay_ms", [700, 1500]))

    async def _solve_recaptcha(self, vcfg):
        selectors = self.selectors.get("recaptcha_iframes", ['iframe[title*="reCAPTCHA"]', 'iframe[src*="google.com/recaptcha"]'])
        for sel in selectors:
            frame_el = await self.page.query_selector(sel)
            if not frame_el:
                continue
            
            frame = await frame_el.content_frame()
            if not frame:
                continue

            await self.human_simulator.async_random_delay(*vcfg.get("recaptcha_before_click_delay_ms", [2500, 4500]))
            
            cb_sels = self.selectors.get("recaptcha_checkboxes", ['.recaptcha-checkbox-border', '.recaptcha-checkbox', 'div[role="checkbox"]'])
            for cb_sel in cb_sels:
                checkbox = await frame.query_selector(cb_sel)
                if not checkbox:
                    continue
                
                box = await checkbox.bounding_box()
                if not box:
                    continue
                
                await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=random.randint(*vcfg.get("checkbox_mouse_steps_range", [10, 20])))
                await self.human_simulator.async_random_delay(*vcfg.get("checkbox_pause_delay_ms", [500, 1200]))
                await checkbox.click()
                return True
        return False

    async def _poll_verification_result(self, vcfg):
        poll_attempts = vcfg.get("result_poll_attempts", 12)
        poll_delay = vcfg.get("result_poll_delay_ms", [2000, 3500])
        scroll_range = vcfg.get("result_poll_scroll_range", [100, 400])
        verify_keyword = self.site_cfg.get("verify_keyword", "verify")
        
        for _ in range(poll_attempts):
            if verify_keyword not in self.page.url:
                logger.info("✅ Verification passed!")
                return True
            await self.human_simulator.async_random_delay(*poll_delay)
            await self.page.mouse.wheel(0, random.randint(*scroll_range))
        return False


    async def navigate_to_home(self):
        """Navigate to the home page"""
        home_url = self.site_cfg.get("home_url", "https://net22.cc/home")
        verify_keyword = self.site_cfg.get("verify_keyword", "verify")
        logger.info(f"🧭 Navigating to {home_url}...")
        
        try:
            await self.page.goto(
                home_url,
                wait_until="domcontentloaded",
                timeout=self.browser_cfg.get("home_navigation_timeout_ms", 45000),
            )
            post_home_min, post_home_max = self.browser_cfg.get("post_home_delay_ms", [2000, 5000])
            await self.human_simulator.async_random_delay(post_home_min, post_home_max)
            
            current_url = self.page.url
            if verify_keyword in current_url:
                logger.info("🔄 Redirected to verification page...")
                success = await self.handle_verification_page()
                if success:
                    post_ver_min, post_ver_max = self.browser_cfg.get("post_verification_delay_ms", [1500, 3500])
                    post_retry_min, post_retry_max = self.browser_cfg.get("post_retry_home_delay_ms", [2000, 4000])
                    await self.human_simulator.async_random_delay(post_ver_min, post_ver_max)
                    await self.page.goto(
                        home_url,
                        wait_until="domcontentloaded",
                        timeout=self.browser_cfg.get("home_navigation_timeout_ms", 45000),
                    )
                    await self.human_simulator.async_random_delay(post_retry_min, post_retry_max)
                else:
                    logger.error("❌ Could not bypass verification.")
                    return False
            
            await self.page.wait_for_selector(
                self.selectors.get("auth_ready", ".searchTab"),
                timeout=self.timeouts.get("auth_ready_wait_ms", 15000),
            )
            logger.info("✅ Successfully authenticated!")
            await self.save_fresh_cookies()
            return True
        except PlaywrightTimeoutError as e:
            logger.error(f"❌ Timeout while navigating to home or waiting for searchTab: {e}")
            raise NavigationError(f"Navigation timed out: {e}")
        except NetflixAuthError:
            raise
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during navigation or authentication: {e}")
            raise NavigationError(f"Unexpected navigation error: {e}")
