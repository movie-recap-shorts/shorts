#!/usr/bin/env python3
"""
Script to refresh YouTube OAuth tokens for all channels
"""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube_uploader import YouTubeUploader
from loguru import logger

def refresh_token(channel_name: str):
    """Refresh token for a specific channel"""
    logger.info(f"Refreshing token for channel: {channel_name}")
    
    uploader = YouTubeUploader(
        credentials_dir='./credentials',
        channel_name=channel_name
    )
    
    # This will open a browser window for authentication
    success = uploader.authenticate(interactive=True)
    
    if success:
        logger.success(f"✅ Token refreshed successfully for {channel_name}")
        
        # Test the authentication by getting channel info
        channel_info = uploader.get_channel_info()
        if channel_info:
            logger.info(f"Channel Title: {channel_info.get('snippet', {}).get('title', 'Unknown')}")
            logger.info(f"Channel ID: {channel_info.get('id', 'Unknown')}")
            
        # Save to Google Sheets
        try:
            from app.services.token_storage import TokenStorage
            storage = TokenStorage()
            
            # Read the fresh token from the file
            with open(uploader.token_file, 'r') as f:
                token_data = json.load(f)
                
            if storage.save_token(channel_name, token_data):
                logger.success(f"✅ Saved new token to Google Sheets for {channel_name}")
            else:
                logger.error("❌ Failed to save token to Google Sheets (check configuration)")
        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            
        return True
    else:
        logger.error(f"❌ Failed to refresh token for {channel_name}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Refresh specific channel
        channel = sys.argv[1]
        refresh_token(channel)
    else:
        # Refresh all channels
        print("Available channels:")
        print("1. movies_en")
        print("2. motivation_en")
        print("\nUsage: python3 refresh_youtube_token.py <channel_name>")
        print("Example: python3 refresh_youtube_token.py movies_en")
