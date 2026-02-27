import argparse
import asyncio
import sys
from .scraper import NetflixScraper
from .ui import UIManager
from .config import load_config
from .installer import ensure_binaries

BANNER = r"""
 _      _____ _____ _____ _     _ ___  _      ____  ____ ____  ____  ____  _____ ____ 
/ \  /|/  __//__ __Y    // \   / \\  \//     / ___\/   _Y  __\/  _ \/  __\/  __//  __\
| |\ |||  \    / \ |  __\| |   | | \  /_____ |    \|  / |  \/|| / \||  \/||  \  |  \/|
| | \|||  /_   | | | |   | |_/\| | /  \\____\\___ ||  \_|    /| |-|||  __/|  /_ |    /
\_/  \|\____\  \_/ \_/   \____/\_//__/\\     \____/\____|_/\_\\_/ \|\_/   \____\\_/\_\
"""

async def run_scraper(query=None, headless=None, download_path=None, config_path=None, browser_type="chromium"):
    # Check for dependencies
    if not ensure_binaries(browser_type):
        sys.exit(1)

    # Load config automatically (picks ~/.netflix-scraper/ or local)
    config = load_config(config_path)
    
    # Apply overrides from CLI
    if headless is not None:
        config.setdefault("browser", {})["headless"] = headless
        
    ui_manager = UIManager(page=None, config=config)
    
    if not download_path:
        default_dir = config.get("app", {}).get("download_dir", "~/Downloads")
        download_path = ui_manager.get_download_path(default_dir)
        
    scraper = NetflixScraper(download_path=download_path, config=config, browser_type=browser_type)
    
    # If query is provided, inject it into the state
    if query:
        scraper.state["search_query"] = query
        
    await scraper.execute_with_retry()

def main():
    print(BANNER)
    parser = argparse.ArgumentParser(description="Netflix Content Scraper CLI")
    parser.add_argument("-q", "--query", help="Search query (movie or series title)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run browser in windowed mode")
    parser.set_defaults(headless=None)
    parser.add_argument("-o", "--output", help="Download directory path")
    parser.add_argument("-c", "--config", help="Specific path to config.yaml")
    parser.add_argument("-b", "--browser", choices=["chromium", "firefox", "webkit"], default="chromium", 
                        help="Browser engine to use (default: chromium)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_scraper(
            query=args.query,
            headless=args.headless,
            download_path=args.output,
            config_path=args.config,
            browser_type=args.browser
        ))
    except KeyboardInterrupt:
        print("\n👋 Program terminated by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
