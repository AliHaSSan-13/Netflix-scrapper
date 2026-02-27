import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import random
from .logger import logger
from .exceptions import BrowserSetupError, NetflixAuthError, NavigationError

class BrowserManager:
    def __init__(self, human_simulator, config=None):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.human_simulator = human_simulator
        self.config = config or {}
        self.browser_cfg = self.config.get("browser", {})
        self.selectors = self.config.get("selectors", {})
        self.timeouts = self.config.get("timeouts", {})
        self.app_cfg = self.config.get("app", {})
        self.site_cfg = self.config.get("site", {})

    async def setup(self):
        """Initialize browser and page with human-like behavior"""
        logger.info("🚀 Launching browser...")
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.firefox.launch(
                headless=self.browser_cfg.get("headless", False),
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
        """
        Load cookies from configured cookies file.
        Applies them to the Playwright browser context.
        """
        cookies_file = self.app_cfg.get("cookies_file", "cookies.json")
        cookies = []

        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)
                logger.info(f"🍪 Loaded existing cookies from {cookies_file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load {cookies_file}: {e}")

        if not cookies:
            logger.warning("⚠️ No cookies loaded. Continuing without preloaded cookies.")

        if cookies:
            try:
                await self.context.add_cookies(cookies)
                logger.info("✅ Cookies applied to browser context!")
            except Exception as e:
                logger.error(f"❌ Error applying cookies to browser context: {e}")
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
        """Handle the verification page with more human-like behavior"""
        vcfg = self.browser_cfg.get("verification", {})
        logger.info("🛡️ Verification page detected... simulating human behavior...")

        try:
            initial_min, initial_max = vcfg.get("initial_delay_ms", [2500, 5500])
            await self.human_simulator.async_random_delay(initial_min, initial_max)

            moves_min, moves_max = vcfg.get("mouse_moves_range", [2, 4])
            sx_min, sx_max = vcfg.get("mouse_start_x_range", [100, 800])
            sy_min, sy_max = vcfg.get("mouse_start_y_range", [100, 600])
            ex_min, ex_max = vcfg.get("mouse_end_x_range", [300, 1000])
            ey_min, ey_max = vcfg.get("mouse_end_y_range", [200, 700])
            step_min, step_max = vcfg.get("mouse_step_delay_s", [0.02, 0.08])
            pause_min, pause_max = vcfg.get("mouse_pause_delay_ms", [500, 1500])
            for _ in range(random.randint(moves_min, moves_max)):
                start_x, start_y = random.randint(sx_min, sx_max), random.randint(sy_min, sy_max)
                end_x, end_y = random.randint(ex_min, ex_max), random.randint(ey_min, ey_max)
                path = self.human_simulator.mouse_movement_pattern(start_x, start_y, end_x, end_y)
                for (x, y) in path:
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(step_min, step_max))
                await self.human_simulator.async_random_delay(pause_min, pause_max)

            scroll_min, scroll_max = vcfg.get("scroll_iterations_range", [2, 4])
            amount_min, amount_max = vcfg.get("scroll_amount_range", [200, 800])
            scroll_pause_min, scroll_pause_max = vcfg.get("scroll_pause_delay_ms", [700, 1500])
            for _ in range(random.randint(scroll_min, scroll_max)):
                scroll_amount = random.randint(amount_min, amount_max)
                direction = random.choice([1, -1])
                await self.page.mouse.wheel(0, scroll_amount * direction)
                await self.human_simulator.async_random_delay(scroll_pause_min, scroll_pause_max)

            recaptcha_iframe = None
            iframe_selectors = self.selectors.get(
                "recaptcha_iframes",
                ['iframe[title*="reCAPTCHA"]', 'iframe[src*="google.com/recaptcha"]'],
            )

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

                recaptcha_wait_min, recaptcha_wait_max = vcfg.get("recaptcha_before_click_delay_ms", [2500, 4500])
                await self.human_simulator.async_random_delay(recaptcha_wait_min, recaptcha_wait_max)

                checkbox_selectors = self.selectors.get(
                    "recaptcha_checkboxes",
                    ['.recaptcha-checkbox-border', '.recaptcha-checkbox', 'div[role="checkbox"]'],
                )
                for selector in checkbox_selectors:
                    checkbox = await frame.query_selector(selector)
                    if checkbox:
                        box = await checkbox.bounding_box()
                        if box:
                            csteps_min, csteps_max = vcfg.get("checkbox_mouse_steps_range", [10, 20])
                            cpause_min, cpause_max = vcfg.get("checkbox_pause_delay_ms", [500, 1200])
                            await self.page.mouse.move(
                                box['x'] + box['width'] / 2,
                                box['y'] + box['height'] / 2,
                                steps=random.randint(csteps_min, csteps_max),
                            )
                            await self.human_simulator.async_random_delay(cpause_min, cpause_max)
                            await checkbox.click()
                            logger.info("✅ Clicked reCAPTCHA checkbox (human-style)")
                            break

            logger.info("⏳ Waiting for verification result...")
            poll_attempts = vcfg.get("result_poll_attempts", 12)
            poll_min, poll_max = vcfg.get("result_poll_delay_ms", [2000, 3500])
            poll_scroll_min, poll_scroll_max = vcfg.get("result_poll_scroll_range", [100, 400])
            verify_keyword = self.site_cfg.get("verify_keyword", "verify")
            for _ in range(poll_attempts):
                current_url = self.page.url
                if verify_keyword not in current_url:
                    logger.info("✅ Verification passed — human behavior succeeded!")
                    return True
                await self.human_simulator.async_random_delay(poll_min, poll_max)
                await self.page.mouse.wheel(0, random.randint(poll_scroll_min, poll_scroll_max))

            logger.warning("❌ Still on verification page after multiple tries.")
            return False

        except Exception as e:
            logger.error(f"❌ Error during verification handling: {e}")
            raise NetflixAuthError(f"Critical error during verification bypass: {e}")

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
