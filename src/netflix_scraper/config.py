import os
from copy import deepcopy
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - defensive runtime guard
    yaml = None # type: ignore


DEFAULT_CONFIG = {
    "app": {
        "state_file": "scraper_state.json",
        "cookies_file": "cookies.json",
        "max_retries": 3,
        "download_dir": "~/Downloads",
    },
    "binaries": {
        "ffmpeg": "ffmpeg",
        "yt_dlp": "yt-dlp",
    },
    "site": {
        "home_url": "https://net22.cc/home",
        "verify_keyword": "verify",
    },
    "network_capture": {
        "intercept_pattern": "**/*",
        "m3u8_indicator": ".m3u8",
        "skip_keywords": ["ping.gif", "drm", "google", "analytics", "jwpltx", "prcdn"],
    },
    "stream_matching": {
        "audio_path_fragment": "/a/",
        "stream_extension": ".m3u8",
        "video_token": "::kp",
        "preferred_video_domain": "net51.cc",
        "preferred_qualities": ["1080p", "720p", "480p", "360p"]
    },
    "browser": {
        "headless": False,
        "launch_args": [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser_check",
        ],
        "viewport": {"width": 1200, "height": 800},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "ignore_https_errors": True,
        "block_resource_pattern": "**/*.{png,jpg,jpeg,webp,svg}",
        "home_navigation_timeout_ms": 45000,
        "post_home_delay_ms": [2000, 5000],
        "post_verification_delay_ms": [1500, 3500],
        "post_retry_home_delay_ms": [2000, 4000],
        "verification": {
            "initial_delay_ms": [2500, 5500],
            "mouse_moves_range": [2, 4],
            "mouse_start_x_range": [100, 800],
            "mouse_start_y_range": [100, 600],
            "mouse_end_x_range": [300, 1000],
            "mouse_end_y_range": [200, 700],
            "mouse_step_delay_s": [0.02, 0.08],
            "mouse_pause_delay_ms": [500, 1500],
            "scroll_iterations_range": [2, 4],
            "scroll_amount_range": [200, 800],
            "scroll_pause_delay_ms": [700, 1500],
            "recaptcha_before_click_delay_ms": [2500, 4500],
            "checkbox_pause_delay_ms": [500, 1200],
            "checkbox_mouse_steps_range": [10, 20],
            "result_poll_attempts": 12,
            "result_poll_delay_ms": [2000, 3500],
            "result_poll_scroll_range": [100, 400],
        },
    },
    "selectors": {
        "auth_ready": ".searchTab",
        "search_button": "button.searchTab",
        "search_input": "input#searchInput",
        "search_results": "div.search-post",
        "search_result_title": "p.fallback-text",
        "search_result_aria_link": "a[aria-label]",
        "season_select": "select.season-box",
        "season_option": "select.season-box option",
        "episode_container": "div.episodeSelector-container",
        "episode_item": "div.episode-item",
        "episode_index": ".titleCard-title_index",
        "episode_title": ".titleCard-title_text",
        "language_list": "div.audio_lang_list",
        "language_option": "div.audio_lang_list a",
        "back_button": "div.btn-payer-back",
        "recaptcha_iframes": [
            'iframe[title*="reCAPTCHA"]',
            'iframe[src*="google.com/recaptcha"]',
        ],
        "recaptcha_checkboxes": [
            ".recaptcha-checkbox-border",
            ".recaptcha-checkbox",
            'div[role="checkbox"]',
        ],
    },
    "timeouts": {
        "auth_ready_wait_ms": 15000,
        "search_results_wait_ms": 15000,
        "languages_wait_ms": 10000,
        "seasons_wait_ms": 3000,
        "episodes_wait_ms": 3000,
        "select_language_wait_ms": 8000,
    },
    "delays": {
        "search_after_fill_ms": [500, 1500],
        "season_change_wait_ms": 2000,
        "episode_capture_wait_ms": [5000, 3000],
        "movie_capture_wait_ms": [5000, 8000],
        "back_navigation_wait_s": 5,
        "language_apply_delay_ms": [1500, 3000],
    },
    "ui": {
        "default_language": "English",
        "preferred_languages": ["english", "hindi"],
    },
    "downloader": {
        "retries": 5,
        "retry_delay_seconds": 5,
        "concurrent_fragments": 16,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "referer": "https://net51.cc/",
        "base_flags": ["--no-part", "--no-warnings", "--newline"],
    },
    "ffmpeg": {
        "overwrite": True,
        "codec_copy": True,
        "movflags_faststart": True,
    },
}


def _deep_merge(base, override):
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_config_dir():
    """Get or create the .netflix-scrapper directory in the user's home folder."""
    config_dir = Path.home() / ".netflix-scrapper"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Directory where this file (and bundled cookies.json) resides
    package_dir = Path(__file__).parent
    
    # Simple migration: Copy local config/cookies if they exist and aren't in home yet
    for filename in ["config.yaml", "cookies.json"]:
        local_file = Path(filename)
        package_file = package_dir / filename
        home_file = config_dir / filename
        
        if not home_file.exists():
            try:
                import shutil
                if local_file.exists():
                    shutil.copy2(local_file, home_file)
                elif package_file.exists():
                    shutil.copy2(package_file, home_file)
            except Exception:
                pass
                
    return config_dir


def load_config(config_path=None):
    """
    Load configuration from the specified path, the home directory, or the current directory.
    Prioritizes home directory config if no path is provided.
    """
    # 1. Determine which config file to use
    if config_path:
        config_file = Path(config_path)
    else:
        # Priority: ~/.netflix-scrapper/config.yaml -> ./config.yaml
        home_config = get_config_dir() / "config.yaml"
        local_config = Path("config.yaml")
        config_file = home_config if home_config.exists() else local_config

    # 2. Return defaults if file doesn't exist
    if not config_file.exists():
        return deepcopy(DEFAULT_CONFIG)

    # 3. Load yaml if available
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to read config files. Install with: pip install PyYAML"
        )

    with config_file.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}

    config = _deep_merge(DEFAULT_CONFIG, loaded)
    
    # Resolve relative paths in 'app' section to absolute paths in config_dir
    # if the file was loaded from or defaults to the home folder
    config_dir = get_config_dir()
    for key in ["state_file", "cookies_file"]:
        val = config.get("app", {}).get(key)
        if val and not os.path.isabs(val):
            config["app"][key] = str(config_dir / val)
            
    return config
