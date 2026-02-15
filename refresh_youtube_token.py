#!/usr/bin/env python3
"""
Script to refresh YouTube OAuth tokens for all channels
"""
import os
import sys
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube_uploader import YouTubeUploader
from loguru import logger

def refresh_token(channel_name: str, force_consent: bool = False):
    """Refresh token for a specific channel"""
    logger.info(f"Refreshing token for channel: {channel_name} (force_consent={force_consent})")
    
    uploader = YouTubeUploader(
        credentials_dir='./credentials',
        channel_name=channel_name
    )
    
    # This will open a browser window for authentication
    success = uploader.authenticate(interactive=True, force_consent=force_consent)
    
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
            
            # Read fresh token and secret
            with open(uploader.token_file, 'r') as f:
                token_data = json.load(f)
            
            secret_data = None
            if uploader.client_secret_file.exists():
                with open(uploader.client_secret_file, 'r') as f:
                    secret_data = json.load(f)

            if storage.save_token(channel_name, token_data, secret_data):
                logger.success(f"✅ Saved new credentials to Google Sheets for {channel_name}")
            else:
                logger.error("❌ Failed to save to Google Sheets")
        except Exception as e:
            logger.error(f"Error saving to Google Sheets: {e}")
            
        return True
    else:
        logger.error(f"❌ Failed to refresh token for {channel_name}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refresh YouTube OAuth tokens")
    parser.add_argument("channel", nargs="?", help="Channel name (movies_en or motivation_en)")
    parser.add_argument("--force", action="store_true", help="Force consent (get fresh refresh token)")
    
    args = parser.parse_args()
    
    if args.channel:
        refresh_token(args.channel, force_consent=args.force)
    else:
        print("Available channels: movies_en, motivation_en")
        print("Usage: python3 refresh_youtube_token.py <channel_name> [--force]")
