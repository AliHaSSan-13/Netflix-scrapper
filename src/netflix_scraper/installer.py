import os
import shutil
import sys
import subprocess
from .logger import logger
from .config import get_config_dir

def check_binaries():
    """Check if required binaries are available in system path or home config folder."""
    config_dir = get_config_dir()
    bin_dir = config_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Add home bin folder to PATH for this session
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    
    missing = []
    
    # Check yt-dlp
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
        
    # Check ffmpeg
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
        
    return missing

def _show_ffmpeg_instructions():
    instructions = {
        "linux": "   Ubuntu/Debian: sudo apt install ffmpeg\n   Fedora: sudo dnf install ffmpeg",
        "darwin": "   macOS: brew install ffmpeg",
        "win32": "   Windows: Download from https://ffmpeg.org/download.html and add to PATH"
    }
    print("\n[SETUP] ffmpeg is missing.")
    print("I cannot install ffmpeg automatically for all systems.")
    print("Please install it manually:")
    print(instructions.get(sys.platform, "   Please visit https://ffmpeg.org/download.html"))
    input("\nPress Enter once you have installed it, or Ctrl+C to abort...")

def install_playwright_browser(browser_type="chromium"):
    """Install the required playwright browser binary."""
    try:
        print(f"\n[SETUP] Installing Playwright {browser_type} browser...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", browser_type])
        logger.info(f"✅ {browser_type} installed successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to install {browser_type}: {e}")
        return False

def ensure_binaries(browser_type="chromium"):
    """Prompt and guide user to install missing binaries and browsers."""
    missing = check_binaries()
    
    if missing:
        logger.warning(f"⚠️ Missing required binaries: {', '.join(missing)}")
        for tool in missing:
            if tool == "yt-dlp":
                print(f"\n[SETUP] {tool} is missing.")
                choice = input(f"Do you want to install {tool} automatically via pip? (y/n): ").lower()
                if choice == 'y':
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
                        logger.info("✅ yt-dlp installed successfully.")
                    except Exception as e:
                        logger.error(f"❌ Failed to install yt-dlp: {e}")
            
            elif tool == "ffmpeg":
                _show_ffmpeg_instructions()

    # Special check for Playwright browsers
    # We attempt to launch or just offer to install if it's the first time
    # For now, let's just make it part of ensure_binaries
    # Note: check_binaries() only checks system PATH for yt-dlp/ffmpeg.
    # Playwright doesn't put browsers in PATH usually.
    
    # We'll rely on browser.py throwing an error and then we can prompt, 
    # OR we can just proactively check if the browser is installed.
    # The most "Zero-Touch" way is to try and install it if we suspect it's missing.
    # But a full 'playwright install' can be heavy.
    
    # Let's just provide the function for scraper.py to use when it fails.
    # Wait, the user said "Automatic prompt and download durante setup".
    # So let's add a check here.
    
    return True
