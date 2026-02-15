"""
TikTok Video Upload Service

This module provides functionality to upload videos to TikTok using the tiktok-uploader library.
This uses a cookie-based approach to bypass the TikTok API approval process.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger
except ImportError as e:
    TIKTOK_UPLOADER_AVAILABLE = False
    logger.warning(f"tiktok-uploader library not found or import failed: {e}. Run: pip install tiktok-uploader")


class TikTokUploader:
    """
    TikTok uploader with cookie-based authentication.
    """
    
    def __init__(
        self,
        credentials_dir: str = "./credentials",
        channel_name: str = "default"
    ):
        """
        Initialize the TikTok uploader.
        
        Args:
            credentials_dir: Directory containing credentials/cookies
            channel_name: Identifier for the channel
        """
        if not TIKTOK_UPLOADER_AVAILABLE:
            raise ImportError("tiktok-uploader library not installed.")
            
        self.credentials_dir = Path(credentials_dir)
        self.channel_name = channel_name
        self.cookies_file = self.credentials_dir / f"{channel_name}_tiktok_cookies.txt"
        
    def upload_video(
        self,
        video_path: str,
        description: str
    ) -> bool:
        """
        Upload a video to TikTok.
        """
        if not self.cookies_file.exists():
            logger.error(f"TikTok cookies file not found: {self.cookies_file}")
            logger.info("Please export your TikTok cookies to this file to enable automation.")
            return False
            
        try:
            logger.info(f"Uploading video to TikTok: {video_path}")
            # tiktok-uploader usually takes the filename as part of the process
            # and uses playwright in the background
            upload_video(
                filename=video_path,
                description=description,
                cookies=str(self.cookies_file)
            )
            logger.success("TikTok upload command executed.")
            return True
            
        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            return False


def upload_to_tiktok(
    video_path: str,
    description: str,
    channel_name: str = "default",
    credentials_dir: str = "./credentials"
) -> bool:
    """Convenience function for TikTok upload."""
    uploader = TikTokUploader(credentials_dir=credentials_dir, channel_name=channel_name)
    return uploader.upload_video(video_path=video_path, description=description)
