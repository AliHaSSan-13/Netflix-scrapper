# Netflix Scrapper

[![PyPI version](https://img.shields.io/pypi/v/netflix-scrapper.svg)](https://pypi.org/project/netflix-scrapper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful CLI tool to automate browser interactions, intercept stream URLs, and download media from streaming mirror sites using `yt-dlp` and `ffmpeg`.

## Important Notice

- This project does **not** use the official Netflix API.
- The implementation targets streaming mirror sites (e.g., `net22.cc`, `net51.cc`) via browser automation.
- **Disclaimer**: You are solely responsible for complying with local laws, platform Terms of Service, and copyright rules. Usage may violate applicable legislation depending on your jurisdiction.

## Quick Start

### 1. Install System Dependencies

You must have **ffmpeg** and **Google Chrome** installed on your system.
- **FFmpeg**: Required to merge video and audio streams seamlessly.
- **Google Chrome**: Required for the browser automation engine.(Any other browser can be used too but you have to pass its flags as an argument) - [see CLI flags](#cli-usage--flags)

#### Installation help for FFmpeg:
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **macOS (Homebrew)**: `brew install ffmpeg`
- **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your system PATH.

### 2. Basic Installation (via Pip)

The fastest way to get started:

```bash
pip install netflix-scrapper
```

### 3. Alternative Installation (Development)

If you want to run the latest code from source:

```bash
git clone https://github.com/AliHaSSan-13/Netflix-scrapper
cd Netflix-scrapper
pip install .
```

### 4. Run the Tool

After installation, you can launch the app directly from your terminal by simply typing:

```bash
netflix-scrapper
```

> **Zero-Touch Onboarding**: On the very first run, the tool automatically detects if `yt-dlp` or browser binaries are missing and offers to install them for you.

## Prerequisites: Authentication Cookies

> **✅ Ready to Go**: The `cookies.json` file is **included** when you install the package via `pip`! The tool uses a default set of cookies out-of-the-box. **NOTE**: The cookies are for firefox browser only.

If the default cookies ever expire or stop working, you can update them using your own active session:

1. Navigate to the mirror site (e.g., `https://net22.cc/home`).
2. Sign in to your account.
3. Use a browser extension (like [Export Cookies](https://chromewebstore.google.com/detail/export-cookie-json-file-f/ghgkfdedpjofehllhlhlanmoojcieefk) or similar) to export your active session cookies as JSON.
4. If you haven't run the tool yet, manually create the config directory: `mkdir -p ~/.netflix-scrapper/`
5. Save the exported JSON file precisely at `~/.netflix-scrapper/cookies.json` (overwriting the default one).

## Features

- **Interactive CLI**: Simple question-and-answer workflow to select titles, languages, and episodes.
- **Zero-Touch Onboarding**: Automatic detection and installation of Chromium (default) and `yt-dlp`.
- **Engine Selection**: Toggle between `chromium`, `firefox`, or `webkit` via flags.
- **Rich Progress Bars**: Enhanced `tqdm` bars with real-time download speed tracking.
- **Human Simulation**: Organic mouse movements and delays to minimize bot detection.
- **Smart Resume**: Persisted run state allows resuming interrupted downloads.

## CLI Usage & Flags

```bash
# Example: Search and run with Firefox engine
netflix-scrapper --query "Breaking Bad" --browser firefox
```

| Flag | Shortcut | Description |
| --- | --- | --- |
| `--query` | `-q` | Initial search string for title. |
| `--browser` | `-b` | Browser engine (`chromium`, `firefox`, `webkit`). |
| `--headless` | | Run without a visible browser window. |
| `--output` | `-o` | Default download directory path. |
| `--config` | `-c` | Path to a custom `config.yaml`. |

## Configuration

Settings are stored in `~/.netflix-scrapper/config.yaml`. You can customize selectors, timeouts, and network interception rules there.

## Troubleshooting

- **`ffmpeg` not found**: Ensure `ffmpeg` is in your system `PATH`.
- **Browser launch failure**: Run `playwright install` or allow the tool to auto-install.
- **Verification Loop**: If blocked, run with `--no-headless` to manually complete the verification if the simulator fails.

## License

MIT License. See `LICENSE` for details.
