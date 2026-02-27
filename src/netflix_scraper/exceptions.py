class NetflixScraperError(Exception):
    """Base class for all exceptions raised by the Netflix Scraper."""
    pass

class BrowserSetupError(NetflixScraperError):
    """Raised when there is an error setting up the browser or Playwright."""
    pass

class NetflixAuthError(NetflixScraperError):
    """Raised when authentication fails (e.g., invalid cookies, verification fails)."""
    pass

class NavigationError(NetflixScraperError):
    """Raised when navigation to a page or element interaction fails/times out."""
    pass

class StreamCaptureError(NetflixScraperError):
    """Raised when the scraper fails to capture valid stream URLs."""
    pass

class DownloadError(NetflixScraperError):
    """Raised when downloading a stream via yt-dlp fails."""
    pass

class MergingError(NetflixScraperError):
    """Raised when merging video and audio streams via ffmpeg fails."""
    pass
