# Netflix Scrapper

A Python automation tool that browses a streaming mirror site, captures `.m3u8` playlist URLs from network traffic, downloads media streams with `yt-dlp`, and merges video/audio into `.mp4` files using `ffmpeg`.

## Important Notice

- This project does **not** use the official Netflix API.
- The current implementation targets `https://net22.cc` (and stream URLs such as `net51.cc`) through browser automation.
- You are responsible for complying with local laws, platform Terms of Service, and copyright rules.

## Features

- Interactive CLI workflow for title/season/episode selection.
- Browser automation via Playwright (Firefox, non-headless).
- Human-like behavior simulation (random delays, mouse movement, scrolling) to reduce bot detection.
- Automatic interception and filtering of `.m3u8` stream URLs.
- Stream download with retry logic using `yt-dlp`.
- Optional video/audio merge via `ffmpeg` with faststart flag.
- Resume support through persisted state (`scraper_state.json`) after interruptions/failures.
- Cookie persistence to reduce repeated verification/login friction.
- Progress feedback in terminal with `tqdm`.

## Tech Stack

- Python (3.10+ recommended; tested layout suggests 3.12)
- [Playwright](https://playwright.dev/python/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)
- `tqdm`, `requests`, `m3u8`

## Repository Structure

```text
.
├── main.py
├── requirements.txt
├── cookies.json
├── browser_headers.json
├── netflix_scraper.log
└── src/netflix_scraper/
    ├── __init__.py
    ├── browser.py          # Browser/context lifecycle, cookies, verification handling
    ├── downloader.py       # yt-dlp async runner + progress parsing
    ├── human_behavior.py   # Randomized delay and mouse movement helpers
    ├── logger.py           # Console + file logging setup
    ├── scraper.py          # End-to-end orchestration + retry + resume state
    ├── ui.py               # Interactive prompts and selection logic
    └── utils.py            # URL categorization and filename sanitization
```

## How It Works

1. `main.py` asks for a destination directory.
2. `NetflixScraper.execute_with_retry()` loads persisted state and runs orchestration.
3. Browser starts via `BrowserManager.setup()` and applies cookies.
4. Scraper navigates to `https://net22.cc/home`, handles verification if needed.
5. User searches and selects title/language/season/episodes.
6. Network interception collects candidate `.m3u8` URLs.
7. URLs are categorized into video/audio streams.
8. Streams are downloaded to temporary files with `yt-dlp`.
9. If audio exists and downloads successfully, `ffmpeg` merges streams; otherwise video-only output is finalized.
10. State is updated continuously and cleaned up when run completes.

## Prerequisites

Before running this project, you must have a valid authenticated session on the target site:

1. Open `https://net22.cc/home` (or search `netmirror` in your browser and open the mirror site).
2. Create/sign in to your account.
3. Use a browser cookie export extension (for example, `Export Cookies`) to export your current session cookies.
4. Paste the exported cookie JSON into `cookies.json` in this repository.

Without valid session cookies in `cookies.json`, authentication and scraping will usually fail.

Install system tools first:

- `ffmpeg`
- `yt-dlp`

Examples:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y ffmpeg yt-dlp
```

Install Python dependencies:

```bash
pip install -r requirements.txt
python -m playwright install firefox
```

## Setup

```bash
git clone <your-repo-url>
cd Netflix-scrapper
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install firefox
```

## Usage

Run:

```bash
python main.py
```

## Configuration

Runtime settings are centralized in `config.yaml` (project root), including:

- target site URL and verification keyword
- selectors and wait timeouts
- stream capture/matching rules
- downloader/ffmpeg binary names and retry behavior
- state/cookie file paths

If `config.yaml` is missing, the app falls back to built-in defaults from `src/netflix_scraper/config.py`.

You will be prompted for:

- Download directory path
- Search query (movie/series)
- Title selection
- Audio language
- Season (if applicable)
- Episode numbers (comma-separated) or Enter for all

## Output Behavior

- Base output folder: `<download_path>/<sanitized_title>/`
- For series with seasons: `<download_path>/<title>/<season>/`
- Final media: `<episode_or_title>.mp4`
- Temporary artifacts during download:
  - `*.video.mp4`
  - `*.audio.m4a`

## State and Resume

The scraper persists run state in `scraper_state.json` (created at project root).

Tracked state includes:

- search query
- selected title/language/season/episodes
- per-item download status (`downloading`, `completed`, `failed`)
- completion flag for full run

On next run, previous choices can be reused and completed items are skipped.

## Cookies

- `cookies.json` is loaded if present and updated after successful navigation/authentication.
- If cookie loading fails or no cookies exist, a static fallback list in `browser.py` is used.
- Keep `cookies.json` private. It may contain session-related identifiers.

## Logging

Configured in `src/netflix_scraper/logger.py`:

- Console: INFO-level plain messages
- File: ERROR-level structured logs (`netflix_scraper.log`)

## Retry and Failure Handling

- Top-level run retry limit: `max_retries = 3` in `NetflixScraper`.
- On unhandled exceptions, the tool prompts whether to retry.
- Temporary files are tracked and cleaned after terminal failure paths.
- If `ffmpeg` is missing, run exits early with an error message.

## Known Limitations

- Site selectors are tightly coupled to current target-site DOM and may break after UI changes.
- Verification/captcha bypass is heuristic and not guaranteed.
- URL selection logic is simplistic (first matching candidates).
- `m3u8` and `requests` are listed dependencies but are not actively used in the current runtime flow.
- Browser runs in headed mode (`headless=False`) by default.

## Security Recommendations

- Add runtime artifacts to `.gitignore`:
  - `cookies.json`
  - `scraper_state.json`
  - `netflix_scraper.log`
  - `__pycache__/`
- Rotate/remove cookies if shared accidentally.
- Avoid storing personal account/session data in the repository.

## Troubleshooting

### `ffmpeg is not installed`
Install `ffmpeg` and ensure it is available in `PATH`.

### `yt-dlp` download failures
- Verify stream URL validity.
- Update `yt-dlp` to latest.
- Check network/firewall/VPN behavior.

### Playwright errors / browser not launching
- Reinstall Playwright browser: `python -m playwright install firefox`
- Ensure required system libraries for Firefox are installed.

### No titles/episodes/languages detected
The target site’s DOM may have changed; update selectors in:

- `src/netflix_scraper/ui.py`
- `src/netflix_scraper/scraper.py`

## Development Notes

Potential improvements:

- Move hard-coded domains/selectors/cookies into config.
- Add structured settings via `.env` or YAML.
- Add automated tests for utils, state transitions, and parser logic.
- Improve stream quality selection and variant playlist handling.
- Add graceful signal handling for Ctrl+C with state flush.

## License

No license file is currently present in this repository.

If you plan to publish this project, add an explicit license (for example, MIT/Apache-2.0) and ensure your use case is legally compliant.
