#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from loguru import logger
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.token_storage import TokenStorage

def test_api_auth():
    if not os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or not os.environ.get("SHEET_ID"):
        logger.error("Missing env vars (GOOGLE_SHEETS_CREDENTIALS, SHEET_ID)")
        return

    storage = TokenStorage()
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

    for channel in ["movies_en", "motivation_en"]:
        logger.info(f"--- Testing LIVE API Auth for {channel} ---")
        token_data, secret_data = storage.get_credentials(channel)
        
        if not token_data:
            logger.warning(f"No token found in Sheet for {channel}")
            continue

        try:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            
            if creds and creds.expired and creds.refresh_token:
                logger.info(f"Attempting to refresh access token using refresh_token...")
                creds.refresh(Request())
                logger.success("✅ Refresh successful!")
            
            # Try a real API call
            youtube = build('youtube', 'v3', credentials=creds)
            request = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True)
            response = request.execute()
            
            if response.get("items"):
                channel_title = response["items"][0]["snippet"]["title"]
                logger.success(f"✅ SUCCESS: Authenticated successfully for '{channel_title}'")
            else:
                logger.error(f"❌ ERROR: Auth seemed to work but no channel items returned.")
        
        except Exception as e:
            logger.error(f"❌ AUTH FAILED for {channel}: {e}")

if __name__ == "__main__":
    test_api_auth()
