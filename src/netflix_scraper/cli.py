import argparse
import asyncio
import sys
from .scraper import NetflixScraper
from .ui import UIManager
from .config import load_config
from .installer import ensure_binaries

BANNER = r"""
  _   _      _    __ _ _                                                    
 | \ | | ___| |_ / _| (_)_  __     ___  ___ _ __ __ _ _ __  _ __   ___ _ __ 
 |  \| |/ _ \ __| |_| | \ \/ /____/ __|/ __| '__/ _` | '_ \| '_ \ / _ \ '__|
 | |\  |  __/ |_|  _| | |>  <_____\__ \ (__| | | (_| | |_) | |_) |  __/ |   
 |_| \_|\___|\__|_| |_|_/_/\_\    |___/\___|_|  \__,_| .__/| .__/ \___|_|   
                                                     |_|   |_|              
"""

async def run_scraper(query=None, headless=None, download_path=None, config_path=None, browser_type="chromium"):
    # Check for dependencies
    if not ensure_binaries(browser_type):
        sys.exit(1)

    import os
    
    # Load config automatically (picks ~/.netflix-scrapper/ or local)
    config = load_config(config_path)
    
    # Check for Cookies to avoid verification loop natively
    cookies_path = config.get("app", {}).get("cookies_file")
    if not cookies_path or not os.path.exists(cookies_path):
        print(f"\n🚫 [ERROR] Authentication cookies not found at '{cookies_path}'")
        print("Netflix-scrapper strictly requires your session cookies to bypass login.")
        print("Please export your cookies from the target streaming site and save them as a JSON file.")
        print("For detailed instructions, see the 'Prerequisites' section in the README.")
        sys.exit(1)
        
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
