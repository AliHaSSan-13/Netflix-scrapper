import asyncio
from typing import Any
import os
import shutil
import json
from .human_behavior import HumanBehaviorSimulator
from .downloader import BrowserM3U8Downloader
from .browser import BrowserManager
from .ui import UIManager
from . import utils
from .logger import logger
from .exceptions import (
    BrowserSetupError,
    NetflixAuthError,
    NavigationError,
    StreamCaptureError,
    DownloadError,
    MergingError
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class NetflixScraper:
    DEFAULT_STATE: dict = {
        "search_query": None,
        "title_selection_index": None,
        "language_selection": None,
        "season_selection_index": None,
        "episode_selections_indices": None,
        "download_progress": {},
        "run_completed": False,
    }

    def __init__(self, download_path, config=None, browser_type="chromium"):
        self.config = config or {}
        self.browser_type = browser_type
        self.app_cfg = self.config.get("app", {})
        self.selectors = self.config.get("selectors", {})
        self.timeouts = self.config.get("timeouts", {})
        self.delays = self.config.get("delays", {})
        
        self.human_simulator = HumanBehaviorSimulator()
        self.browser_manager = BrowserManager(self.human_simulator, config=self.config)
        self.downloader: Any = None
        self.ui_manager: Any = None
        self.page: Any = None
        self.context: Any = None
        
        self.m3u8_urls = []
        self._cleanup_files = []
        self.state_file = self.app_cfg.get("state_file", "scraper_state.json")
        self.state = self.DEFAULT_STATE.copy()
        
        self.capture_cfg = self.config.get("network_capture", {})
        self.stream_cfg = self.config.get("stream_matching", {})
        self.binaries_cfg = self.config.get("binaries", {})
        self.ffmpeg_cfg = self.config.get("ffmpeg", {})
        self.max_retries = self.app_cfg.get("max_retries", 3)
        self.download_path = download_path
        self.video_path = None

    def load_state(self):
        """Load state from file or set defaults."""
        if not os.path.exists(self.state_file):
            self.state = self.DEFAULT_STATE.copy()
            return

        try:
            with open(self.state_file, 'r') as f:
                self.state = {**self.DEFAULT_STATE, **json.load(f)}
            logger.info("🔄 Resuming from previous state.")
        except Exception as e:
            logger.warning(f"⚠️ State reset: {e}")
            self.state = self.DEFAULT_STATE.copy()

    def save_state(self):
        """Save the current state to a file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            logger.warning(f"⚠️ Could not save state file: {e}")

    def cleanup_state_file(self):
        """Remove the state file."""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                logger.info("🗑️ Removed state file.")
            except OSError as e:
                logger.warning(f"⚠️ Could not remove state file: {e}")

    def cleanup_temp_files(self):
        """Remove all temporary download files."""
        logger.info("🧹 Cleaning up all temporary files...")
        for f in self._cleanup_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    logger.info(f"🗑️ Removed temp file: {f}")
            except OSError as e:
                logger.warning(f"⚠️ Could not delete temp file {f}: {e}")

    async def execute_with_retry(self):
        """Execute the scraper with a retry mechanism."""
        self.load_state()
        if self.state.get('run_completed'):
            logger.info("✅ Previous run completed successfully. Nothing to do.")
            self.cleanup_state_file()
            return

        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                await self.run()
                logger.info("✅ Scraper finished successfully.")
                self.cleanup_state_file()
                break

            except NetflixAuthError as e:
                logger.error(f"🔐 Authentication Error: {e}")
                logger.info("Auth errors often require manual cookie updates. Aborting for safety.")
                self.cleanup_state_file()
                break

            except (BrowserSetupError, MergingError) as e:
                logger.error(f"⚙️ System/Merging Error: {e}")
                retry_count += 1
                if retry_count > self.max_retries:
                    self.cleanup_temp_files()
                    break
                logger.info(f"🔄 Retrying after system error... ({retry_count}/{self.max_retries})")
                await asyncio.sleep(5)

            except (asyncio.CancelledError, KeyboardInterrupt):
                logger.info("\n🛑 Termination signal received. Cleaning up...")
                self.cleanup_temp_files()
                self.cleanup_state_file()
                raise

            except Exception as e:
                logger.error(f"❌ Unexpected Error: {e}")
                import traceback
                logger.error(traceback.format_exc())

                retry_count += 1
                if retry_count > self.max_retries:
                    logger.error("🚫 Maximum retry limit reached. Aborting.")
                    self.cleanup_temp_files()
                    self.cleanup_state_file()
                    break

                try:
                    user_choice = input("Do you want to retry? (y/n): ").lower()
                except (EOFError, KeyboardInterrupt):
                    user_choice = 'n'

                if user_choice != 'y':
                    logger.info("Aborting run.")
                    self.cleanup_temp_files()
                    self.cleanup_state_file()
                    break
                else:
                    logger.info(f"🔄 Retrying... (Attempt {retry_count}/{self.max_retries})")

    async def setup(self):
        """Initialize browser and page with human-like behavior"""
        try:
            self.page, self.context = await self.browser_manager.setup(self.browser_type)
            await self.setup_request_interception()
            await self.browser_manager.set_cookies()
            self.downloader = BrowserM3U8Downloader(self.context, config=self.config)
            self.ui_manager = UIManager(self.page, config=self.config)
        except Exception as e:
            logger.error(f"❌ Failed to set up scraper: {e}")
            raise

    async def close(self):
        """Close browser and playwright."""
        try:
            await self.browser_manager.close()
        except Exception:
            pass

    async def setup_request_interception(self):
        """Set up request interception to capture m3u8 URLs"""
        try:
            await self.page.route(
                self.capture_cfg.get("intercept_pattern", "**/*"),
                self.route_handler,
            )
        except Exception as e:
            logger.error(f"❌ Failed to set up request interception: {e}")
            raise

    async def route_handler(self, route):
        """Capture only meaningful .m3u8 URLs"""
        request = route.request
        url = request.url.lower()
        m3u8_indicator = self.capture_cfg.get("m3u8_indicator", ".m3u8")
        skip_keywords = self.capture_cfg.get(
            "skip_keywords",
            ["ping.gif", "drm", "google", "analytics", "jwpltx", "prcdn"],
        )

        if m3u8_indicator in url:
            if any(skip in url for skip in skip_keywords):
                await route.continue_()
                return
            logger.info(f"🎯 Captured potential stream URL: {request.url}")
            self.m3u8_urls.append(request.url)
        await route.continue_()

    async def run(self):
        """Main function to run the scraper and downloader for a single attempt."""
        ffmpeg_bin = self.binaries_cfg.get("ffmpeg", "ffmpeg")
        if not shutil.which(ffmpeg_bin):
            logger.error("❌ ffmpeg is not installed. Please install it to merge video and audio.")
            return

        try:
            logger.info("🤖 Starting Netflix scraper...")
            await self.setup()

            if not await self.browser_manager.navigate_to_home():
                raise NetflixAuthError("Failed to authenticate or bypass verification")

            await self._navigate_to_results()
            
            titles = await self.ui_manager.get_search_results()
            if not titles:
                logger.info("No search results found!")
                return

            selection = await self._get_title_selection(titles)
            safe_title = utils.sanitize_filename(titles[selection])
            self.video_path = os.path.join(self.download_path, safe_title)
            os.makedirs(self.video_path, exist_ok=True)

            await self._select_title(selection)
            
            lang = await self._get_language_selection()
            await self.select_language(lang)

            seasons = await self.get_seasons()
            if seasons:
                season_choice = await self._get_season_selection(seasons)
                await self.select_season(season_choice)
                
                episodes = await self.get_episodes()
                if episodes:
                    await self._process_episodes(episodes, seasons[season_choice]['text'])
                else:
                    await self._process_movie(titles[selection])
            else:
                await self._process_movie(titles[selection])

            self.state['run_completed'] = True
            self.save_state()

        finally:
            await self.close()

    async def _navigate_to_results(self):
        """Handle search navigation and input."""
        try:
            await self.page.click(self.selectors.get("search_button", "button.searchTab"))
        except Exception as e:
            raise NavigationError(f"Error clicking search button: {e}")

        search_query = self.state.get("search_query") or input("🔍 Search the movie/series you want: ")
        if not self.state.get("search_query"):
            self.state["search_query"] = search_query
            self.save_state()

        try:
            await self.page.fill(self.selectors.get("search_input", "input#searchInput"), search_query)
        except Exception as e:
            raise NavigationError(f"Error filling search input: {e}")

        delay = self.delays.get("search_after_fill_ms", [500, 1500])
        await self.human_simulator.async_random_delay(*delay)

    async def _get_title_selection(self, titles):
        selection = self.state.get("title_selection_index")
        if selection is None:
            selection = self.ui_manager.get_user_selection(titles, "title")
            self.state["title_selection_index"] = selection
            self.save_state()
        return selection

    async def _select_title(self, selection):
        results = await self.page.query_selector_all(self.selectors.get("search_results", "div.search-post"))
        try:
            await results[selection].click()
        except Exception as e:
            raise NavigationError(f"Error clicking search result: {e}")

    async def _get_language_selection(self):
        lang = self.state.get("language_selection")
        if not lang:
            lang = await self.ui_manager.get_language_selection()
            self.state["language_selection"] = lang
            self.save_state()
        return lang

    async def _get_season_selection(self, seasons):
        choice = self.state.get("season_selection_index")
        if choice is None:
            choice = self.ui_manager.get_user_selection([s['text'] for s in seasons], "season")
            self.state["season_selection_index"] = choice
            self.save_state()
        return choice

    async def _process_episodes(self, episodes, season_text):
        selected_episodes = self.state.get("episode_selections_indices")
        if selected_episodes is None:
            selected_episodes = self.ui_manager.get_episode_selection(episodes)
            self.state["episode_selections_indices"] = selected_episodes
            self.save_state()

        episode_elements = await self.page.query_selector_all(self.selectors.get("episode_item", "div.episode-item"))

        for episode_index in selected_episodes:
            if 0 <= episode_index < len(episode_elements):
                await self._process_single_episode(episodes[episode_index], episode_elements[episode_index], season_text)

    async def _process_single_episode(self, episode_data, element, season_text):
        logger.info(f"\n🔗 Processing Episode {episode_data['number']}: {episode_data['title']}")
        self.m3u8_urls = []
        await self.capture_episode_m3u8(element)

        if not self.m3u8_urls:
            logger.info(f"❌ No URLs captured for: {episode_data['title']}")
            return

        working_video, working_audio = self._extract_working_streams(episode_data['title'])
        if working_video:
            await self._download_and_merge_episode(episode_data, working_video, working_audio, season_text=season_text)
        else:
            raise StreamCaptureError(f"No working video stream for: {episode_data['title']}")

        await self._go_back()

    async def _process_movie(self, title):
        movie_data = {'title': title}
        safe_title = utils.sanitize_filename(title)
        
        if self.state["download_progress"].get(safe_title) == "completed":
            logger.info(f"✅ Movie '{title}' already downloaded.")
            return

        m3u8_urls = await self.handle_movie_or_single_episode()
        if not m3u8_urls:
            logger.info(f"❌ No URLs captured for movie: {title}")
            return

        working_video, working_audio = self._extract_working_streams(title, m3u8_urls)
        if working_video:
            await self._download_and_merge_episode(movie_data, working_video, working_audio)
        else:
            logger.error(f"❌ No working video stream for movie: {title}")

    def _extract_working_streams(self, title, urls=None):
        target_urls = list(set(urls or self.m3u8_urls))
        logger.info(f"🔍 Found {len(target_urls)} unique URLs for {title}")
        
        video_urls, audio_urls = utils.categorize_m3u8_urls(
            target_urls,
            audio_path_fragment=self.stream_cfg.get("audio_path_fragment", "/a/"),
            stream_extension=self.stream_cfg.get("stream_extension", ".m3u8"),
            video_token=self.stream_cfg.get("video_token", "::kp"),
        )
        return utils.find_working_urls(
            video_urls, audio_urls,
            preferred_video_domain=self.stream_cfg.get("preferred_video_domain", "net51.cc")
        )

    async def _go_back(self):
        try:
            await self.page.click(self.selectors.get("back_button", "div.btn-payer-back"))
            await asyncio.sleep(self.delays.get("back_navigation_wait_s", 5))
        except Exception as e:
            logger.error(f"❌ Error clicking back button: {e}")

    async def _download_and_merge_episode(self, episode_data, working_video, working_audio, season_text=None):
        """Download video and audio streams and merge them."""
        title = episode_data['title']
        safe_title = utils.sanitize_filename(title)

        if self.state["download_progress"].get(safe_title) == "completed":
            logger.info(f"✅ '{title}' already downloaded. Skipping.")
            return

        video_path = self.video_path
        if not video_path:
            raise DownloadError("Download path not initialized.")
            
        if season_text:
            video_path = os.path.join(video_path, utils.sanitize_filename(season_text))
            os.makedirs(video_path, exist_ok=True)
            
        final_output = os.path.join(video_path, f"{safe_title}.mp4")
        temp_v = os.path.join(video_path, f"{safe_title}.v.mp4")
        temp_a = os.path.join(video_path, f"{safe_title}.a.m4a")

        self._cleanup_files.extend([temp_v, temp_a])
        self.state["download_progress"][safe_title] = "downloading"
        self.save_state()

        logger.info(f"\n🎬 Downloading: {title}")
        if not await self.downloader.download_m3u8_with_ytdlp(working_video, temp_v):
            self.state["download_progress"][safe_title] = "failed"
            self.save_state()
            raise DownloadError(f"Video download failed for {title}")

        audio_success = False
        if working_audio:
            audio_success = await self.downloader.download_m3u8_with_ytdlp(working_audio, temp_a)
            if not audio_success:
                logger.warning(f"⚠️ Audio download failed for {title}. Proceeding with video only.")

        if audio_success:
            await self._merge_streams(temp_v, temp_a, final_output, safe_title)
        else:
            os.rename(temp_v, final_output)
            self._cleanup_files.remove(temp_v)

        self.state["download_progress"][safe_title] = "completed"
        self.save_state()

    async def _merge_streams(self, video, audio, output, safe_title):
        logger.info("🎛️ Merging streams...")
        cmd = [self.binaries_cfg.get("ffmpeg", "ffmpeg"), "-y", "-i", video, "-i", audio]
        if self.ffmpeg_cfg.get("codec_copy", True):
            cmd.extend(["-c", "copy"])
        if self.ffmpeg_cfg.get("movflags_faststart", True):
            cmd.extend(["-movflags", "+faststart"])
        cmd.append(output)

        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            if proc.returncode != 0:
                raise MergingError(f"ffmpeg failed with code {proc.returncode}")
            
            logger.info(f"✅ Done: {output}")
            for f in [video, audio]:
                if os.path.exists(f):
                    os.remove(f)
                if f in self._cleanup_files:
                    self._cleanup_files.remove(f)
        except Exception as e:
            self.state["download_progress"][safe_title] = "failed"
            self.save_state()
            raise MergingError(f"Merge error: {e}")

        self.state["download_progress"][safe_title] = "completed"
        self.save_state()

    async def get_seasons(self):
        """Get available seasons if they exist"""
        logger.info("Checking for seasons...")
        try:
            await self.page.wait_for_selector(
                self.selectors.get("season_select", "select.season-box"),
                timeout=self.timeouts.get("seasons_wait_ms", 3000),
            )
            season_options = await self.page.query_selector_all(self.selectors.get("season_option", "select.season-box option"))

            seasons = []
            for option in season_options:
                try:
                    season_text = await option.text_content()
                    season_value = await option.get_attribute('value')
                    seasons.append({
                        'text': season_text.strip(),
                        'value': season_value,
                    })
                except Exception as e:
                    logger.error(f"Error parsing season option: {e}")
                    continue

            return seasons
        except PlaywrightTimeoutError:
            logger.info("No season selector found within timeout.")
            return []
        except Exception as e:
            logger.error(f"❌ Error getting seasons: {e}")
            return []

    async def select_season(self, season_index):
        """Select specific season"""
        try:
            season_options = await self.page.query_selector_all(self.selectors.get("season_option", "select.season-box option"))
            if 0 <= season_index < len(season_options):
                value = await season_options[season_index].get_attribute('value')
                await self.page.select_option(self.selectors.get("season_select", "select.season-box"), value)
                await self.page.wait_for_timeout(self.delays.get("season_change_wait_ms", 2000))
                logger.info(f"✅ Selected season: {await season_options[season_index].text_content()}")
                return True
            else:
                logger.warning(f"❌ Invalid season index {season_index}")
                return False
        except Exception as e:
            logger.error(f"❌ Error selecting season: {e}")
            return False

    async def get_episodes(self):
        """Get episodes if they exist"""
        logger.info("Checking for episodes...")
        try:
            await self.page.wait_for_selector(
                self.selectors.get("episode_container", "div.episodeSelector-container"),
                timeout=self.timeouts.get("episodes_wait_ms", 3000),
            )
            episodes = await self.page.query_selector_all(self.selectors.get("episode_item", "div.episode-item"))
            episode_data = []

            for episode in episodes:
                try:
                    index_element = await episode.query_selector(self.selectors.get("episode_index", ".titleCard-title_index"))
                    episode_num = await index_element.text_content() if index_element else "N/A"

                    title_element = await episode.query_selector(self.selectors.get("episode_title", ".titleCard-title_text"))
                    title = await title_element.text_content() if title_element else "Unknown Title"

                    episode_id = await episode.get_attribute('data-ep_id')

                    episode_data.append({
                        'number': episode_num.strip(),
                        'title': title.strip(),
                        'id': episode_id,
                    })
                except Exception as e:
                    logger.error(f"Error parsing episode: {e}")
                    continue

            return episode_data
        except PlaywrightTimeoutError:
            logger.info("No episode list found within timeout.")
            return []
        except Exception as e:
            logger.error(f"❌ Error getting episodes: {e}")
            return []

    async def capture_episode_m3u8(self, episode_element):
        """Capture m3u8 URL for a specific episode"""
        try:
            current_count = len(self.m3u8_urls)
            await episode_element.click()
            for wait_ms in self.delays.get("episode_capture_wait_ms", [5000, 3000]):
                await self.page.wait_for_timeout(wait_ms)

            new_urls = len(self.m3u8_urls) - current_count
            logger.info(f"📡 Captured {new_urls} new URLs for this episode")
            return new_urls > 0
        except PlaywrightTimeoutError:
            logger.warning("❌ Timeout while waiting for episode to load after click.")
            return False
        except Exception as e:
            logger.error(f"Error capturing m3u8 for episode: {e}")
            return False

    async def handle_movie_or_single_episode(self):
        """Handle movies or single episodes"""
        logger.info("🎬 This appears to be a movie or single episode")

        original_url_count = len(self.m3u8_urls)
        logger.info("Clicking play button...")
        try:
            await self.page.click(self.selectors.get("play_button", "a.playLink.modal-main-play"))
        except Exception:
            logger.warning("Play button not found.")
            pass

        logger.info("🔄 Video may auto-play, waiting for stream to load...")
        try:
            movie_wait_min, movie_wait_max = self.delays.get("movie_capture_wait_ms", [5000, 8000])
            await self.human_simulator.async_random_delay(movie_wait_min, movie_wait_max)
        except Exception as e:
            logger.warning(f"Error during random delay: {e}")

        if len(self.m3u8_urls) > original_url_count:
            new_urls = self.m3u8_urls[original_url_count:]
            logger.info(f"✅ Successfully captured {len(new_urls)} URLs")

            m3u8_indicator = self.capture_cfg.get("m3u8_indicator", ".m3u8")
            skip_keywords = self.capture_cfg.get("skip_keywords", ["ping.gif"])
            filtered_urls = [
                url for url in new_urls
                if m3u8_indicator in url and not any(skip in url for skip in skip_keywords)
            ]
            logger.info(f"🔍 Filtered to {len(filtered_urls)} valid m3u8 URLs")

            return filtered_urls
        else:
            logger.warning("❌ No new URLs captured")
            return []

    async def select_language(self, language):
        """Select language"""
        logger.info(f"🌐 Selecting language: {language}")
        try:
            await self.page.wait_for_selector(
                self.selectors.get("language_list", "div.audio_lang_list"),
                timeout=self.timeouts.get("select_language_wait_ms", 8000),
            )

            lang_link = self.page.locator(
                f'{self.selectors.get("language_option", "div.audio_lang_list a")}:has-text("{language}")'
            )
            if await lang_link.count() > 0:
                await lang_link.click()
                delay_min, delay_max = self.delays.get("language_apply_delay_ms", [1500, 3000])
                await self.human_simulator.async_random_delay(delay_min, delay_max)
                return True
            else:
                logger.warning(f"Language {language} not found")
                return False
        except PlaywrightTimeoutError:
            logger.error(f"❌ Timeout while waiting for language list or element for {language}.")
            return False
        except Exception as e:
            logger.error(f"Error selecting language: {e}")
            return False
