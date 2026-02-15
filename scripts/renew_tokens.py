#!/usr/bin/env python3
"""
Renew YouTube OAuth tokens and save them back to Google Sheets.
This script is intended to be run in GitHub Actions every few days.
"""
import os
import sys
import json
from pathlib import Path
from loguru import logger

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.youtube_uploader import YouTubeUploader
from app.services.token_storage import TokenStorage

def renew_and_sync(channel_name: str):
    """
    1. Authenticate (will refresh access token if needed)
    2. Save fresh token back to Google Sheets
    """
    logger.info(f"🔄 Processing token renewal for channel: {channel_name}")
    
    # Initialize uploader (should already have token file from github_env_setup.py)
    uploader = YouTubeUploader(channel_name=channel_name)
    
    # This will refresh the token automatically if it's expired
    if uploader.authenticate(interactive=False):
        logger.success(f"✅ Successfully authenticated/refreshed token for {channel_name}")
        
        # Now save the refreshed token back to Google Sheets
        storage = TokenStorage()
        try:
            with open(uploader.token_file, 'r') as f:
                token_data = json.load(f)
            
            if storage.save_token(channel_name, token_data):
                logger.success(f"🚀 Saved refreshed token for {channel_name} to Google Sheets")
            else:
                logger.error(f"❌ Failed to save refreshed token for {channel_name} to Google Sheets")
        except Exception as e:
            logger.error(f"Error reading/saving token: {e}")
    else:
        logger.error(f"❌ Failed to authenticate/refresh token for {channel_name}. Manual re-auth may be required.")

if __name__ == "__main__":
    # Get channel name from environment or run for both
    target_channel = os.environ.get("CHANNEL_NAME")
    if target_channel:
        renew_and_sync(target_channel)
    else:
        # Default behavior: try both
        for channel in ["movies_en", "motivation_en"]:
            renew_and_sync(channel)
