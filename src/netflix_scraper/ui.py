import os
from .logger import logger

class UIManager:
    def __init__(self, page, config=None):
        self.page = page
        self.config = config or {}
        self.selectors = self.config.get("selectors", {})
        self.timeouts = self.config.get("timeouts", {})
        self.ui_cfg = self.config.get("ui", {})

    def get_download_path(self):
        """Get and validate the download path from the user."""
        while True:
            download_path = input("Enter the path to store the videos: ").strip()
            if os.path.isdir(download_path):
                return download_path
            else:
                logger.warning("Invalid path! Please enter a valid directory path.")

    async def get_search_results(self):
        """Get and display search results"""
        logger.info("📋 Fetching search results...")
        try:
            await self.page.wait_for_selector(
                self.selectors.get("search_results", "div.search-post"),
                timeout=self.timeouts.get("search_results_wait_ms", 15000),
            )
            
            results = await self.page.query_selector_all(
                self.selectors.get("search_results", "div.search-post")
            )
            
            titles = []
            for i, result in enumerate(results):
                try:
                    title_element = await result.query_selector(
                        self.selectors.get("search_result_title", "p.fallback-text")
                    )
                    if title_element:
                        title = await title_element.text_content()
                        titles.append(title.strip())
                    else:
                        link_element = await result.query_selector(
                            self.selectors.get("search_result_aria_link", "a[aria-label]")
                        )
                        if link_element:
                            title = await link_element.get_attribute('aria-label')
                            titles.append(title.strip())
                        else:
                            titles.append(f"Unknown Title {i+1}")
                except Exception as e:
                    logger.error(f"Error getting title {i+1}: {e}")
                    titles.append(f"Error getting title {i+1}")
            
            return titles
        except Exception as e:
            logger.error(f"Could not fetch search results: {e}")
            return []

    def get_user_selection(self, items, item_name):
        """Get user selection from a list of items."""
        logger.info(f"\n🎬 Available {item_name}s:")
        for i, item in enumerate(items):
            logger.info(f"{i+1}. {item}")
        
        while True:
            try:
                selection = int(input(f"\nSelect a {item_name} (1-{len(items)}): ")) - 1
                if 0 <= selection < len(items):
                    return selection
                else:
                    logger.warning("Invalid selection!")
            except ValueError:
                logger.warning("Please enter a valid number!")
    
    def get_episode_selection(self, episodes):
        """Get user selection for episodes."""
        logger.info(f"\n🎭 Found {len(episodes)} episode(s)")
        for i, episode in enumerate(episodes):
            logger.info(f"{i+1}. Episode {episode['number']}: {episode['title']}")
        
        episode_input = input(f"\nEnter episode numbers (comma-separated, or press Enter for all 1-{len(episodes)}): ").strip()
        
        if episode_input == "":
            selected_episodes = list(range(len(episodes)))
        else:
            try:
                selected_episodes = [int(x.strip()) - 1 for x in episode_input.split(',')]
                selected_episodes = [ep for ep in selected_episodes if 0 <= ep < len(episodes)]
                if not selected_episodes:
                    selected_episodes = list(range(len(episodes)))
            except ValueError:
                selected_episodes = list(range(len(episodes)))
        
        return selected_episodes

    async def get_language_selection(self):
        """Get available languages and prompt user for selection."""
        logger.info("\n🌐 Fetching available languages...")
        try:
            default_language = self.ui_cfg.get("default_language", "English")
            preferred_language_keys = self.ui_cfg.get("preferred_languages", ["english", "hindi"])
            await self.page.wait_for_selector(
                self.selectors.get("language_option", "div.audio_lang_list a"),
                timeout=self.timeouts.get("languages_wait_ms", 10000),
            )
            language_elements = await self.page.query_selector_all(
                self.selectors.get("language_option", "div.audio_lang_list a")
            )
            available_languages = []

            for element in language_elements:
                text = await element.text_content()
                if text:
                    clean_text = text.strip()
                    if clean_text.lower() != "unknown":
                        available_languages.append(clean_text)

            if not available_languages:
                logger.warning(f"❌ No valid languages found, defaulting to {default_language}.")
                return default_language

            preferred_langs = [lang for lang in available_languages if lang.lower() in preferred_language_keys]

            if preferred_langs:
                logger.info("\n🌐 Preferred languages available:")
                for i, pl in enumerate(preferred_langs, 1):
                    logger.info(f"{i}. {pl}")
                logger.info("A. Show all languages")

                while True:
                    user_input = input("\nSelect a language (1/2) or type 'A' to see all: ").strip().lower()
                    if user_input == 'a':
                        logger.info("\n🌐 All available languages:")
                        for i, lang_option in enumerate(available_languages, 1):
                            logger.info(f"{i}. {lang_option}")
                        while True:
                            try:
                                choice = int(input(f"\nSelect language (1-{len(available_languages)}): "))
                                if 1 <= choice <= len(available_languages):
                                    return available_languages[choice - 1]
                                else:
                                    logger.warning("Invalid selection.")
                            except ValueError:
                                logger.warning("Please enter a valid number.")
                    else:
                        try:
                            choice = int(user_input)
                            if 1 <= choice <= len(preferred_langs):
                                return preferred_langs[choice - 1]
                            else:
                                logger.warning("Invalid selection.")
                        except ValueError:
                            logger.warning("Please enter a valid input.")
            else:
                logger.info("\n🌐 Available languages:")
                for i, lang_option in enumerate(available_languages, 1):
                    logger.info(f"{i}. {lang_option}")
                while True:
                    try:
                        choice = int(input(f"\nSelect language (1-{len(available_languages)}): "))
                        if 1 <= choice <= len(available_languages):
                            return available_languages[choice - 1]
                        else:
                            logger.warning("Invalid selection.")
                    except ValueError:
                        logger.warning("Please enter a valid number.")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch language list: {e}")
            return self.ui_cfg.get("default_language", "English")
