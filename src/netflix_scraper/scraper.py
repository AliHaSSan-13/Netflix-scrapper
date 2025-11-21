import asyncio
import os
import subprocess
import shutil
import json
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError # Import TimeoutError

from .human_behavior import HumanBehaviorSimulator
from .downloader import BrowserM3U8Downloader
from .browser import BrowserManager
from .ui import UIManager
from . import utils
import time
from .logger import logger

class NetflixScraper:
    def __init__(self, download_path):
        self.human_simulator = HumanBehaviorSimulator()
        self.browser_manager = BrowserManager(self.human_simulator)
        self.m3u8_urls = []
        self.downloader = None
        self._cleanup_files = []
        self.page = None
        self.context = None
        self.ui_manager = None
        self.state_file = "scraper_state.json"
        self.state = {}
        self.max_retries = 3
        self.download_path = download_path
        self.video_path = None

    def load_state(self):
        """Load state from a file if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.info("🔄 Resuming from previous state.")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"⚠️ Could not load state file, starting fresh: {e}")
                self.state = {}
        
        if not self.state:
            self.state = {
                "search_query": None,
                "title_selection_index": None,
                "language_selection": None,
                "season_selection_index": None,
                "episode_selections_indices": None,
                "download_progress": {},  # e.g., { "safe_title": "completed" }
                "run_completed": False
            }

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

            except Exception as e:
                logger.error(f"❌ An error occurred during execution: {e}")
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
            self.page, self.context = await self.browser_manager.setup()
            await self.setup_request_interception()
            await self.browser_manager.set_cookies()
            self.downloader = BrowserM3U8Downloader(self.context)
            self.ui_manager = UIManager(self.page)
        except Exception as e:
            logger.error(f"❌ Failed to set up scraper: {e}")
            raise

    async def close(self):
        """Close browser and playwright."""
        await self.browser_manager.close()

    async def setup_request_interception(self):
        """Set up request interception to capture m3u8 URLs"""
        try:
            await self.page.route("**/*", self.route_handler)
        except Exception as e:
            logger.error(f"❌ Failed to set up request interception: {e}")
            raise

    async def route_handler(self, route):
        """Capture only meaningful .m3u8 URLs"""
        request = route.request
        url = request.url.lower()

        if ".m3u8" in url:
            if any(skip in url for skip in ["ping.gif", "drm", "google", "analytics", "jwpltx", "prcdn"]):
                await route.continue_()
                return
            logger.info(f"🎯 Captured potential stream URL: {request.url}")
            self.m3u8_urls.append(request.url)
        await route.continue_()

    async def run(self):
        """Main function to run the scraper and downloader for a single attempt."""

        if not shutil.which("ffmpeg"):
            logger.error("❌ ffmpeg is not installed. Please install it to merge video and audio.")
            return

        try:
            logger.info("🤖 Starting Netflix scraper...")
            await self.setup()

            auth_success = await self.browser_manager.navigate_to_home()
            if not auth_success:
                raise Exception("Failed to authenticate or bypass verification")

            try:
                await self.page.click('button.searchTab')
            except PlaywrightTimeoutError:
                raise Exception("Timeout while clicking search button. Element not found or not clickable.")
            except Exception as e:
                raise Exception(f"Error clicking search button: {e}")

            if self.state.get("search_query"):
                search_query = self.state["search_query"]
                logger.info(f"Found search query in state: '{search_query}'")
            else:
                search_query = input("the movie/series you want to search: ")
                self.state["search_query"] = search_query
                self.save_state()

            try:
                await self.page.fill('input#searchInput', search_query)
            except PlaywrightTimeoutError:
                raise Exception("Timeout while filling search input. Element not found.")
            except Exception as e:
                raise Exception(f"Error filling search input: {e}")

            await self.human_simulator.async_random_delay(500, 1500)

            titles = await self.ui_manager.get_search_results()
            if not titles:
                logger.info("No search results found!")
                return

            if self.state.get("title_selection_index") is not None:
                selection = self.state["title_selection_index"]
                logger.info(f"Found title selection in state: {titles[selection]}")
            else:
                selection = self.ui_manager.get_user_selection(titles, "title")
                self.state["title_selection_index"] = selection
                self.save_state()

            safe_title = utils.sanitize_filename(titles[selection])
            self.video_path = os.path.join(self.download_path, safe_title)
            os.makedirs(self.video_path, exist_ok=True)

            results = await self.page.query_selector_all('div.search-post')
            try:
                await results[selection].click()
            except PlaywrightTimeoutError:
                raise Exception("Timeout while clicking search result. Element not found or not clickable.")
            except Exception as e:
                raise Exception(f"Error clicking search result: {e}")

            if self.state.get("language_selection"):
                lang = self.state["language_selection"]
                logger.info(f"Found language selection in state: {lang}")
            else:
                lang = await self.ui_manager.get_language_selection()
                self.state["language_selection"] = lang
                self.save_state()

            await self.select_language(lang)

            seasons = await self.get_seasons()

            if seasons:
                if self.state.get("season_selection_index") is not None:
                    season_choice = self.state["season_selection_index"]
                    logger.info(f"Found season selection in state: {seasons[season_choice]['text']}")
                else:
                    season_choice = self.ui_manager.get_user_selection([s['text'] for s in seasons], "season")
                    self.state["season_selection_index"] = season_choice
                    self.save_state()

                await self.select_season(season_choice)

                episodes = await self.get_episodes()
                if episodes:
                    if self.state.get("episode_selections_indices") is not None:
                        selected_episodes = self.state["episode_selections_indices"]
                        logger.info(f"Found episode selection in state: {', '.join([str(i+1) for i in selected_episodes])}")
                    else:
                        selected_episodes = self.ui_manager.get_episode_selection(episodes)
                        self.state["episode_selections_indices"] = selected_episodes
                        self.save_state()

                    episode_elements = await self.page.query_selector_all('div.episode-item')

                    for i, episode_index in enumerate(selected_episodes):
                        if 0 <= episode_index < len(episode_elements):
                            episode_data = episodes[episode_index]
                            logger.info(f"\n🔗 Processing Episode {episode_data['number']}: {episode_data['title']}")

                            self.m3u8_urls = [] # Clear URLs for the new episode
                            await self.capture_episode_m3u8(episode_elements[episode_index])

                            current_episode_m3u8_urls = list(self.m3u8_urls)

                            if current_episode_m3u8_urls:
                                unique_urls = list(set(current_episode_m3u8_urls))
                                logger.info(f"🔍 After removing duplicates: {len(unique_urls)} unique URLs for {episode_data['title']}")
                                video_urls, audio_urls = utils.categorize_m3u8_urls(unique_urls)
                                working_video, working_audio = utils.find_working_urls(video_urls, audio_urls)

                                if working_video:
                                    season_text = seasons[season_choice]['text']
                                    await self._download_and_merge_episode(episode_data, working_video, working_audio, season_text=season_text)
                                else:
                                    logger.error(f"❌ Failed to find a working video stream for: {episode_data['title']}")
                            else:
                                logger.info(f"\n❌ No URLs were captured for episode: {episode_data['title']}")

                            # Click the back button to return to episode selection
                            try:
                                await self.page.click('div.btn-payer-back')
                                time.sleep(5) # Wait for navigation back
                            except PlaywrightTimeoutError:
                                logger.error("❌ Timeout while clicking back button. Element not found or not clickable.")
                            except Exception as e:
                                logger.error(f"❌ Error clicking back button: {e}")

            else: # This block handles movies or single episodes
                movie_data = {'title': titles[selection]} # Create a dictionary for consistency
                safe_title = utils.sanitize_filename(movie_data['title'])

                if self.state["download_progress"].get(safe_title) == "completed":
                    logger.info(f"✅ Movie '{movie_data['title']}' already downloaded. Skipping.")
                    return 

                m3u8_urls = await self.handle_movie_or_single_episode()
                if m3u8_urls:
                    unique_urls = list(set(m3u8_urls))
                    logger.info(f"🔍 After removing duplicates: {len(unique_urls)} unique URLs for {movie_data['title']}")
                    video_urls, audio_urls = utils.categorize_m3u8_urls(unique_urls)
                    working_video, working_audio = utils.find_working_urls(video_urls, audio_urls)

                    if working_video:
                        await self._download_and_merge_episode(movie_data, working_video, working_audio)
                    else:
                        logger.error(f"❌ Failed to find a working video stream for: {movie_data['title']}")
                else:
                    logger.info(f"\n❌ No URLs were captured for movie: {movie_data['title']}")

            self.state['run_completed'] = True
            self.save_state()

        finally:
            await self.close()

    async def _download_and_merge_episode(self, episode_data, working_video, working_audio, season_text=None):
        """Download video and audio streams and merge them."""
        safe_title = utils.sanitize_filename(episode_data['title'])
        
        if self.state["download_progress"].get(safe_title) == "completed":
            logger.info(f"✅ Episode '{episode_data['title']}' already downloaded. Skipping.")
            return

        video_path = self.video_path
        if season_text:
            season_folder_name = utils.sanitize_filename(season_text)
            video_path = os.path.join(self.video_path, season_folder_name)
            os.makedirs(video_path, exist_ok=True)

        final_output = os.path.join(video_path, f"{safe_title}.mp4")
        temp_video = os.path.join(video_path, f"{safe_title}.video.mp4")
        temp_audio = os.path.join(video_path, f"{safe_title}.audio.m4a")

        self._cleanup_files.extend([temp_video, temp_audio])

        logger.info(f"\n🎬 Downloading episode: {episode_data['title']}")
        self.state["download_progress"][safe_title] = "downloading"
        self.save_state()

        video_success = False
        if working_video:
            video_success = await self.downloader.download_m3u8_with_ytdlp(working_video, temp_video)

        if not video_success:
            self.state["download_progress"][safe_title] = "failed"
            self.save_state()
            raise Exception(f"Video download failed for {episode_data['title']}")

        audio_success = False
        if working_audio:
            audio_success = await self.downloader.download_m3u8_with_ytdlp(working_audio, temp_audio)
        
        if working_audio and not audio_success:
            logger.warning(f"⚠️ Audio download failed for {episode_data['title']}. Proceeding with video only.")

        if audio_success:
            logger.info("🎛️ Merging video and audio streams...")
            merge_cmd = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-i", temp_audio,
                "-c", "copy",
                "-movflags", "+faststart",
                final_output
            ]
            try:
                subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                logger.info(f"✅ Download and merge complete: {final_output}")
                # Remove temporary files after successful merge
                if os.path.exists(temp_video): os.remove(temp_video)
                if os.path.exists(temp_audio): os.remove(temp_audio)
                self._cleanup_files = [f for f in self._cleanup_files if f not in (temp_video, temp_audio)]
            except subprocess.CalledProcessError as e:
                self.state["download_progress"][safe_title] = "failed"
                self.save_state()
                logger.error(f"ffmpeg stderr: {e.stderr.decode()}")
                raise Exception("ffmpeg merge failed. Video and audio part files are kept.")

            except Exception as e:
                self.state["download_progress"][safe_title] = "failed"
                self.save_state()
                raise Exception(f"An unexpected error occurred during ffmpeg merge: {e}")

        else:
            logger.info("✅ Video download complete. No audio to merge or audio download failed. Renaming video file.")
            try:
                os.rename(temp_video, final_output)
                self._cleanup_files = [f for f in self._cleanup_files if f != temp_video]
            except Exception as e:
                self.state["download_progress"][safe_title] = "failed"
                self.save_state()
                raise Exception(f"An unexpected error occurred during file rename: {e}")

        self.state["download_progress"][safe_title] = "completed"
        self.save_state()


    async def get_seasons(self):
        """Get available seasons if they exist"""
        logger.info("Checking for seasons...")
        try:
            await self.page.wait_for_selector('select.season-box', timeout=3000)
            season_options = await self.page.query_selector_all('select.season-box option')
            
            seasons = []
            for option in season_options:
                try:
                    season_text = await option.text_content()
                    season_value = await option.get_attribute('value')
                    seasons.append({
                        'text': season_text.strip(),
                        'value': season_value
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
            season_options = await self.page.query_selector_all('select.season-box option')
            if 0 <= season_index < len(season_options):
                value = await season_options[season_index].get_attribute('value')
                await self.page.select_option('select.season-box', value)
                await self.page.wait_for_timeout(2000)
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
            await self.page.wait_for_selector('div.episodeSelector-container', timeout=3000)
            episodes = await self.page.query_selector_all('div.episode-item')
            episode_data = []

            for episode in episodes:
                try:
                    index_element = await episode.query_selector('.titleCard-title_index')
                    episode_num = await index_element.text_content() if index_element else "N/A"

                    title_element = await episode.query_selector('.titleCard-title_text')
                    title = await title_element.text_content() if title_element else "Unknown Title"

                    episode_id = await episode.get_attribute('data-ep_id')

                    episode_data.append({
                        'number': episode_num.strip(),
                        'title': title.strip(),
                        'id': episode_id
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
            await self.page.wait_for_timeout(5000) # Wait for page to potentially load new m3u8s after click
            await self.page.wait_for_timeout(3000) # Additional wait
            
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
        
        logger.info("🔄 Video should auto-play, waiting for stream to load...")
        try:
            await self.human_simulator.async_random_delay(5000, 8000)
        except Exception as e:
            logger.warning(f"Error during random delay: {e}")

        
        if len(self.m3u8_urls) > original_url_count:
            new_urls = self.m3u8_urls[original_url_count:]
            logger.info(f"✅ Successfully captured {len(new_urls)} URLs")
            
            filtered_urls = [url for url in new_urls if '.m3u8' in url and 'ping.gif' not in url]
            logger.info(f"🔍 Filtered to {len(filtered_urls)} valid m3u8 URLs")
            
            return filtered_urls
        else:
            logger.warning("❌ No new URLs captured")
            return []
    
    async def select_language(self, language):
        """Select language"""
        logger.info(f"🌐 Selecting language: {language}")
        try:
            await self.page.wait_for_selector('div.audio_lang_list', timeout=8000)
            
            lang_link = self.page.locator(f'div.audio_lang_list a:has-text("{language}")')
            if await lang_link.count() > 0:
                await lang_link.click()
                await self.human_simulator.async_random_delay(1500, 3000)
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
