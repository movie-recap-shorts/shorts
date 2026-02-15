#!/usr/bin/env python3
"""
Sync local YouTube tokens to Google Sheets.
Usage:
    GOOGLE_SHEETS_CREDENTIALS='{...}' SHEET_ID='...' python3 scripts/upload_tokens.py
"""
import os
import sys
import json
from pathlib import Path
from loguru import logger

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.token_storage import TokenStorage

def upload_local_tokens():
    """Reads tokens from credentials/ directory and uploads to Google Sheets."""
    root_dir = Path(__file__).parent.parent
    creds_dir = root_dir / "credentials"
    
    storage = TokenStorage()
    
    # Identify available tokens
    channels = ["movies_en", "motivation_en"]
    found_any = False
    
    for channel in channels:
        token_file = creds_dir / f"{channel}_token.json"
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                
                logger.info(f"📤 Uploading current token for {channel} to Google Sheets...")
                if storage.save_token(channel, token_data):
                    logger.success(f"✅ Successfully uploaded {channel} token.")
                    found_any = True
                else:
                    logger.error(f"❌ Failed to upload {channel} token.")
            except Exception as e:
                logger.error(f"Error processing {channel}: {e}")
        else:
            logger.warning(f"No local token found for {channel} at {token_file}")

    if not found_any:
        logger.warning("No tokens were found to upload. Make sure you have refreshed them locally first.")

if __name__ == "__main__":
    if not os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or not os.environ.get("SHEET_ID"):
        print("\n❌ Error: Missing environment variables!")
        print("Please run this command with your Google Sheets credentials:")
        print("GOOGLE_SHEETS_CREDENTIALS='{...}' SHEET_ID='...' python3 scripts/upload_tokens.py")
        sys.exit(1)
    
    upload_local_tokens()
