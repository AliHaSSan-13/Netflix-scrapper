# Netflix Scraper

A powerful CLI tool to automate browser interactions, intercept stream URLs, and download media from streaming mirror sites using `yt-dlp` and `ffmpeg`.

## Important Notice

- This project does **not** use the official Netflix API.
- The current implementation targets streaming mirror sites (e.g., `net22.cc`, `net51.cc`) via browser automation.
- **Disclaimer**: You are solely responsible for complying with local laws, platform Terms of Service, and copyright rules. Usage may violate applicable legislation depending on your jurisdiction.

## Quick Start

### 1. Install System Dependencies

You absolutely need `ffmpeg` installed on your system to merge the video and audio streams seamlessly.
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **macOS (Homebrew)**: `brew install ffmpeg`
- **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your system PATH.

### 2. Install the Package

We recommend installing the package into an isolated virtual environment:

```bash
# Clone the repository
git clone https://github.com/AliHaSSan-13/Netflix-scrapper
cd Netflix-scrapper

# Create a virtual environment and activate it
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the CLI tool
pip install .
```

### 3. Run the Tool

Once installed, you can launch the app directly from your terminal:

```bash
netflix-scraper
```

> **Zero-Touch Onboarding**: On your very first run, the tool will automatically detect if `yt-dlp` or browser binaries are missing and offer to install them for you. No manual downloading required!

## Prerequisites: Authentication Cookies

Before scraping, you must provide a valid authenticated session for the target site to bypass login forms.

1. Open your browser and navigate to the mirror site (e.g., `https://net22.cc/home`).
2. Create an account or sign in.
3. Use a browser extension (like "Export Cookies") to export your active session cookies as JSON.
4. The CLI will automatically create a configuration directory at `~/.netflix-scraper/`. Save your exported JSON file there as `~/.netflix-scraper/cookies.json`.

*(If the configuration directory does not exist yet, you can run the tool once and let it fail, which will auto-generate the folder, or just create it manually).*

## Features

- **Interactive CLI**: Simple question-and-answer workflow to select titles, languages, seasons, and episodes.
- **Zero-Touch Onboarding**: Automatic detection and installation of Chromium (default engine) and `yt-dlp`.
- **Flexible Browser Support**: Seamlessly switch between Chromium, Firefox, or WebKit.
- **Rich User Experience**: Custom ASCII art banner and enhanced progress bars (`tqdm`) with real-time speed tracking.
- **Cross-Platform Sandboxing**: Settings and session states are safely tucked away in your home directory (`~/.netflix-scraper/`).
- **Human-like Behavior**: Emulates real user interactions (mouse movements, scrolling, organic delays) to reduce bot detection.
- **Smart Resume**: State persistency allows you to resume broken or interrupted downloads without starting over.

## CLI Usage & Flags

You can bypass some of the interactive prompts by passing arguments directly:

```bash
# Search directly for a movie and start downloading with Firefox engine
netflix-scraper --query "Breaking Bad" --browser firefox
```

| Flag | Shortcut | Description |
| --- | --- | --- |
| `--query` | `-q` | Initial search string (e.g., movie or series title). |
| `--browser` | `-b` | Select execution engine (`chromium`, `firefox`, `webkit`). Default is `chromium`. |
| `--headless` | | Run the browser invisibly in the background. |
| `--no-headless` | | Force the browser window to be visible during execution. |
| `--output` | `-o` | Setup a default destination directory for downloads. |
| `--config` | `-c` | Override default settings with a custom `config.yaml` path. |

## Configuration

Runtime settings are fully customizable. The tool looks for configuration in:
1. Custom `--config` flag path.
2. User directory: `~/.netflix-scraper/config.yaml`.
3. It initializes with sensible fallbacks if none are found.

You can customize variables like target site URLs, default download paths, request wait timeouts, simulated human delays, ffmpeg strictness, etc.

### Output Behavior
- Base Output: `<download_path>/<sanitized_title>/`
- Formatted File: `<download_path>/<title>/<season>/<episode_or_title>.mp4`

## Troubleshooting

- **`ffmpeg` is not recognized**: Ensure `ffmpeg` is actually installed and added to your OS `PATH` variable.
- **Downloads randomly failing**: Verify that `yt-dlp` is up-to-date. Streaming sites frequently change their backend APIs.
- **Browser fails to launch**: Run `python -m playwright install` or let the CLI's auto-installer take over. You might also be missing system dependencies for Linux browsers; install them with `npx playwright install-deps`.
- **Stuck at verification loop**: The target site's Captcha might have flagged the bot. Restart the app using the `--no-headless` flag so you can manually solve it if needed.

## Architecture Highlights
- Uses **Playwright** to orchestrate browser routing and DOM mutations.
- Network traffic interceptors sniff for `.m3u8` payloads and dynamically extract media streaming tokens.
- **yt-dlp** orchestrates fragmented downloading.
- **ffmpeg** is sub-processed to weave and merge audio fragments with video fragments safely via the `movflags_faststart` option.

## License

This project is licensed under the **MIT License**.

- **Commercial & Private Use**: Allowed.
- **Modification & Distribution**: Allowed.
- **Warranty/Liability**: None. The software is provided "as-is".

*For the complete legal text, refer to the `LICENSE` file in this repository.*
