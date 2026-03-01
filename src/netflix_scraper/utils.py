import re
from .logger import logger

def categorize_m3u8_urls(urls, audio_path_fragment="/a/", stream_extension=".m3u8", video_token="::kp"):
    """Categorize URLs into video and audio streams"""
    video_urls = []
    audio_urls = []
    
    for url in urls:
        if audio_path_fragment in url and url.endswith(stream_extension):
            audio_urls.append(url)
        elif video_token in url and audio_path_fragment not in url:
            video_urls.append(url)
    
    logger.info(f"📹 Video URLs: {len(video_urls)}")
    logger.info(f"🔊 Audio URLs: {len(audio_urls)}")
    return video_urls, audio_urls

def find_working_urls(video_urls, audio_urls, preferred_video_domain="net51.cc", preferred_qualities=None):
    """Find working video and audio URLs, preferring specified qualities"""
    if preferred_qualities is None:
        preferred_qualities = ["1080p", "720p", "480p", "360p"]
        
    logger.info(f"\n🔍 Found {len(video_urls)} video URL(s) and {len(audio_urls)} audio URL(s)")
    
    working_video = None
    working_audio = audio_urls[0] if audio_urls else None
    
    # 1. Look for explicit qualities first
    for quality in preferred_qualities:
        for url in video_urls:
            if quality in url.lower():
                working_video = url
                logger.info(f"🎯 Selected high-quality ({quality}) video URL: {working_video}")
                return working_video, working_audio
                
    # 2. Look for master url fallback
    for url in video_urls:
        if preferred_video_domain in url:
            working_video = url
            logger.info(f"🎯 Selected master video URL: {working_video}")
            break
    
    # 3. If no master found, use the first video URL
    if not working_video and video_urls:
        working_video = video_urls[0]
        logger.info(f"🎯 Selected first available video URL: {working_video}")
    
    return working_video, working_audio

def sanitize_filename(filename):
    """Sanitize a string to be used as a filename."""
    return re.sub(r'[\\/*?:\"<>|]', "_", filename)
