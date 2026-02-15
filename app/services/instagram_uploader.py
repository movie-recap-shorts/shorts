"""
Instagram Reels Upload Service

This module provides functionality to upload videos to Instagram Reels using the instagrapi library.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger
try:
    from instagrapi import Client
    INSTAGRAPI_AVAILABLE = True
except ImportError as e:
    INSTAGRAPI_AVAILABLE = False
    logger.warning(f"instagrapi library not found or import failed: {e}. Run: pip install instagrapi")


class InstagramUploader:
    """
    Instagram Reels uploader with session management.
    """
    
    def __init__(
        self,
        credentials_dir: str = "./credentials",
        channel_name: str = "default"
    ):
        """
        Initialize the Instagram uploader.
        
        Args:
            credentials_dir: Directory containing credentials/sessions
            channel_name: Identifier for the channel
        """
        if not INSTAGRAPI_AVAILABLE:
            raise ImportError("instagrapi library not installed.")
            
        self.credentials_dir = Path(credentials_dir)
        self.channel_name = channel_name
        self.session_file = self.credentials_dir / f"{channel_name}_ig_session.json"
        
        # Support both 'creds' and 'cred' naming variants
        self.creds_file = self.credentials_dir / f"{channel_name}_ig_creds.json"
        if not self.creds_file.exists():
            self.creds_file = self.credentials_dir / f"{channel_name}_ig_cred.json"
            
        self.cl = Client()
        
    def authenticate(self) -> bool:
        """
        Authenticate with Instagram.
        Uses cached session if available, otherwise logs in with credentials.
        """
        try:
            # 1. Try to load session
            if self.session_file.exists():
                logger.info(f"Loading Instagram session for {self.channel_name}")
                self.cl.load_settings(self.session_file)
                self.cl.login_by_sessionid(self.cl.session_id)
                try:
                    self.cl.get_timeline_feed()
                    logger.success(f"Instagram session valid for {self.channel_name}")
                    return True
                except Exception:
                    logger.warning("Instagram session expired, logging in again")
            
            # 2. Login with credentials
            if not self.creds_file.exists():
                logger.error(f"Instagram credentials file not found: {self.creds_file}")
                return False
                
            with open(self.creds_file, "r") as f:
                creds = json.load(f)
                username = creds.get("username")
                password = creds.get("password")
            
            if not username or not password:
                logger.error("Instagram username/password missing in creds file")
                return False
                
            logger.info(f"Logging into Instagram as {username}")
            self.cl.login(username, password)
            self.cl.dump_settings(self.session_file)
            logger.success(f"Successfully logged into Instagram for {self.channel_name}")
            return True
            
        except Exception as e:
            logger.error(f"Instagram authentication failed: {e}")
            return False
            
    def upload_reels(
        self,
        video_path: str,
        caption: str,
        thumbnail_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a video to Instagram Reels.
        """
        if not self.authenticate():
            return None
            
        try:
            logger.info(f"Uploading Reels to Instagram: {video_path}")
            media = self.cl.clip_upload(
                path=video_path,
                caption=caption,
                thumbnail=thumbnail_path
            )
            logger.success(f"Reels uploaded successfully! Media ID: {media.pk}")
            return {"id": media.pk, "url": f"https://www.instagram.com/reels/{media.code}/"}
            
        except Exception as e:
            logger.error(f"Instagram Reels upload failed: {e}")
            return None


def upload_video_to_instagram(
    video_path: str,
    caption: str,
    channel_name: str = "default",
    credentials_dir: str = "./credentials"
) -> Optional[Dict[str, Any]]:
    """Convenience function for Instagram upload."""
    uploader = InstagramUploader(credentials_dir=credentials_dir, channel_name=channel_name)
    return uploader.upload_reels(video_path=video_path, caption=caption)
