import asyncio
import os
import re
import math
from tqdm import tqdm
from .logger import logger
from .exceptions import DownloadError

class BrowserM3U8Downloader:
    def __init__(self, context, config=None):
        self.context = context
        cfg = (config or {}).get("downloader", {})
        binaries = (config or {}).get("binaries", {})
        self.retries = cfg.get("retries", 5)
        self.retry_delay_seconds = cfg.get("retry_delay_seconds", 5)
        self.concurrent_fragments = str(cfg.get("concurrent_fragments", 16)) # Increased for native parallel fetching
        self.user_agent = cfg.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self.referer = cfg.get("referer", "https://net51.cc/")
        
        self.base_flags = cfg.get("base_flags", [
            "--no-part", 
            "--no-warnings", 
            "--newline",
            "--retries", "10",              # Resilient but not eternal
            "--fragment-retries", "10",
            "--skip-unavailable-fragments",
            "--no-mtime",                   # Faster filesystem operations
            "--hls-use-mpegts",             # Critical for mirror sites stability
            "--http-chunk-size", "10M",     # Larger chunks reduce request overhead
            "--buffer-size", "16M",         # High-speed buffer
            "--resize-buffer",              # Dynamic buffer management
            "--socket-timeout", "30",
            "--file-access-provided",       # Optimization for modern filesystems
            "--downloader", "m3u8:native",  # Stick to native as requested
            "--hls-prefer-native",          # Ensure native HLS handling
            "--retry-sleep", "fragment:exp=1:20:http&extractor:exp=1:20",
        ])
        self.yt_dlp_binary = binaries.get("yt_dlp", "yt-dlp")
        
    async def download_m3u8_with_ytdlp(self, m3u8_url, output_name="output.mp4"):
        if not m3u8_url:
            return False

        logger.info(f"🎯 Downloading: {m3u8_url}")

        ytdlp_cmd = [
            self.yt_dlp_binary,
            *self.base_flags,
            "--concurrent-fragments", self.concurrent_fragments,
            "--user-agent", self.user_agent,
            "--referer", self.referer,
            "-o", output_name,
            m3u8_url,
        ]

        for attempt in range(self.retries):
            pbar = None
            process = None
            try:
                process = await asyncio.create_subprocess_exec(
                    *ytdlp_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                stdout_lines = []
                if process.stdout:
                    async for raw_line in process.stdout:
                        line = raw_line.decode(errors="ignore").strip()
                        stdout_lines.append(line)
                        
                        percent, speed, eta = self._parse_progress(line)
                        if percent is not None:
                            if pbar is None:
                                pbar = self._create_pbar(output_name, line)
                            pbar.n = percent
                            postfix = {}
                            if speed:
                                postfix["speed"] = speed
                            if eta:
                                postfix["eta"] = eta
                            pbar.set_postfix(postfix, refresh=True)
                            pbar.refresh()
                
                await process.wait()
                if pbar:
                    pbar.close()

                if process.returncode == 0:
                    logger.info(f"✅ Download complete: {output_name}")
                    return True
                
                logger.warning(f"❌ yt-dlp failed (attempt {attempt+1}/{self.retries}) Code: {process.returncode}")
                for line in stdout_lines[-5:]:
                    logger.debug(f"yt-dlp: {line}")

            except (asyncio.CancelledError, KeyboardInterrupt):
                if process:
                    try:
                        logger.info(f"⚠️ Terminating yt-dlp process for {output_name}...")
                        process.terminate()
                        await process.wait()
                    except Exception:
                        pass
                if pbar:
                    pbar.close()
                raise
            except Exception as e:
                logger.error(f"❌ Exception during download attempt {attempt + 1}/{self.retries}: {e}")
                if pbar:
                    pbar.close()
            
            delay = self.retry_delay_seconds * (math.pow(2, attempt))
            logger.info(f"⌛ Retrying after {delay:.1f} seconds...")
            await asyncio.sleep(delay)

        logger.error(f"❌ Failed to download after {self.retries} attempts: {m3u8_url}")
        raise DownloadError(f"yt-dlp failed after {self.retries} attempts for: {m3u8_url}")
        
        return False
    
    def _parse_progress(self, line):
        percent = None
        speed = ""
        eta = ""
        
        if m := re.search(r"\[download\]\s+(\d+\.\d+)%", line):
            percent = float(m.group(1))
            
        if m := re.search(r"at\s+([\d\.]+(?:[kKMmGg]iB|B)/s)", line):
            speed = m.group(1)
            
        if m := re.search(r"ETA\s+([\d:]+)", line):
            eta = m.group(1)
            
        return percent, speed, eta

    def _create_pbar(self, path, first_line):
        name = os.path.basename(path)
        if len(name) > 30:
            name = name[:27] + "..."
            
        desc = f"⬇️ {name}"
        if m := re.search(r"of\s+~?([\d\.]+)(\w+iB)", first_line):
            desc += f" ({m.group(1)}{m.group(2)})"
            
        pbar = tqdm(
            total=100,
            desc=desc,
            bar_format="{l_bar}{bar} | {n:.1f}% | {postfix}",
            unit="%",
            dynamic_ncols=True,
            leave=True
        )
        pbar.set_postfix_str("calc...")
        return pbar