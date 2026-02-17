#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.token_storage import TokenStorage

def check_sheet():
    if not os.environ.get("GOOGLE_SHEETS_CREDENTIALS") or not os.environ.get("SHEET_ID"):
        print("Missing env vars")
        return

    storage = TokenStorage()
    for channel in ["movies_en", "motivation_en"]:
        try:
            token, secret = storage.get_credentials(channel)
            if token:
                print(f"--- {channel} ---")
                print(f"Client ID: {token.get('client_id', 'None')}")
                print(f"Has Refresh Token: {bool(token.get('refresh_token'))}")
                print(f"Has Client Secret: {bool(secret)}")
                print(f"Token Expiry: {token.get('expiry', 'None')}")
            else:
                print(f"--- {channel} NOT FOUND ---")
        except Exception as e:
            print(f"--- {channel} ERROR: {e}")

if __name__ == "__main__":
    check_sheet()
