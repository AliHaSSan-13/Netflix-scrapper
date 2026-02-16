import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from netflix_scraper.scraper import NetflixScraper
from netflix_scraper.ui import UIManager
from netflix_scraper.config import load_config

async def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = load_config(config_path)
    ui_manager = UIManager(page=None, config=config)
    download_path = ui_manager.get_download_path()
    scraper = NetflixScraper(download_path=download_path, config=config)
    await scraper.execute_with_retry()

if __name__ == "__main__":
    asyncio.run(main())
