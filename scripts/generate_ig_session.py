import json
import os
import sys
from pathlib import Path
from instagrapi import Client
from loguru import logger

def generate_session(channel_name="motivation_en", credentials_dir="./credentials"):
    credentials_dir = Path(credentials_dir)
    creds_file = credentials_dir / f"{channel_name}_ig_cred.json"
    session_file = credentials_dir / f"{channel_name}_ig_session.json"

    if not creds_file.exists():
        logger.error(f"Credentials file not found: {creds_file}")
        return

    with open(creds_file, "r") as f:
        creds = json.load(f)
        username = creds.get("username")
        password = creds.get("password")

    if not username or not password:
        logger.error("Username or password missing in creds file")
        return

    cl = Client()
    
    try:
        logger.info(f"Attempting to login to Instagram as {username}...")
        cl.login(username, password)
        cl.dump_settings(session_file)
        logger.success(f"Session successfully generated and saved to {session_file}")
        logger.info("You can now push this file to GitHub or copy its content to a GitHub Secret.")
    except Exception as e:
        logger.error(f"Login failed: {e}")
        if "Challenge" in str(e):
            logger.warning("Instagram triggered a challenge. Please log in manually on your phone/browser first, or use a proxy.")

if __name__ == "__main__":
    generate_session()
