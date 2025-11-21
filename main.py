import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from netflix_scraper.scraper import NetflixScraper
from netflix_scraper.ui import UIManager

async def main():
    ui_manager = UIManager(page=None)
    download_path = ui_manager.get_download_path()
    scraper = NetflixScraper(download_path=download_path)
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
