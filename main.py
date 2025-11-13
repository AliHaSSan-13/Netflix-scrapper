import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from netflix_scraper.scraper import NetflixScraper

async def main():
    scraper = NetflixScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
