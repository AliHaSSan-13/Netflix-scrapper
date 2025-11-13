import asyncio
from .logger import logger
import re
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://net20.cc/"
}

class BrowserM3U8Downloader:
    def __init__(self, context, max_workers=16, timeout=10, retries=3):
        self.context = context
        self.max_workers = max_workers
        self.timeout = timeout
        self.retries = retries
        
    async def download_m3u8_with_ytdlp(self, m3u8_url, output_name="output.mp4"):
        if not m3u8_url:
            return False

        logger.info(f"🎯 Downloading: {m3u8_url}")

        ytdlp_cmd = [
            "yt-dlp",
            "--no-part",
            "--no-warnings",
            "--newline",
            "--concurrent-fragments", "4",
            "--user-agent", HEADERS["User-Agent"],
            "--referer", "https://net51.cc/",
            "-o", output_name,
            m3u8_url,
        ]

        for attempt in range(self.retries):
            pbar = None
            try:
                process = await asyncio.create_subprocess_exec(
                    *ytdlp_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                pbar_desc = f"⬇️ Downloading"
                stdout_lines = []

                async for raw_line in process.stdout:
                    line = raw_line.decode(errors="ignore").strip()
                    stdout_lines.append(line)
                    
                    patterns = [
                        r"\[download\]\s+(\d+\.\d+)%.*?of\s+([\d\.]+)(\w+iB).*?at\s+([\d\.]+\w+/s)",
                        r"\[download\]\s+(\d+\.\d+)%.*?of\s+~?([\d\.]+)(\w+iB).*?at\s+([\d\.]+\w+/s)",
                        r"\[download\]\s+(\d+\.\d+)%",
                        r"\[download\]\s+.*?(\d+\.\d+)%.*?of\s+([\d\.]+)(\w+iB)",
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            percent = float(match.group(1))
                            
                            if pbar is None:
                                total_size, total_unit = "Unknown", ""
                                if len(match.groups()) >= 3:
                                    total_size, total_unit = match.group(2), match.group(3)
                                    pbar_desc = f"⬇️ Downloading {output_name} ({total_size}{total_unit})"
                                
                                pbar = tqdm(
                                    total=100,
                                    desc=pbar_desc,
                                    bar_format="{l_bar}{bar} | {n:.1f}/{total}%",
                                    unit="%",
                                    dynamic_ncols=True
                                )
                            
                            pbar.n = percent
                            pbar.refresh()
                            break

                await process.wait()
                
                if pbar:
                    pbar.n = 100
                    pbar.refresh()
                    pbar.close()

                if process.returncode == 0:
                    logger.info(f"✅ Download complete: {output_name}")
                    return True
                else:
                    logger.warning(f"❌ yt-dlp failed on attempt {attempt + 1}/{self.retries} with return code: {process.returncode}")
                    logger.debug("".join(stdout_lines))

            except Exception as e:
                logger.error(f"❌ Exception during download attempt {attempt + 1}/{self.retries}: {e}")
                if pbar:
                    pbar.close()
            
            await asyncio.sleep(5) # Wait 5 seconds before retrying

        logger.error(f"❌ Failed to download after {self.retries} attempts: {m3u8_url}")
        return False
