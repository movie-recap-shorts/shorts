#!/usr/bin/env python3
"""
Download high-quality meme reaction clips from Vlipsy.com.
These clips are specifically chosen for the meme-surprise video format.
"""
import os
import sys
import requests
import json
import time
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MEME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resource", "memes")
# Use the proven public API key for Vlipsy
VLIPSY_API_KEY = "vl_hFxn07bG43d0n9t"
VLIPSY_API_BASE = "https://apiv2.vlipsy.com/v1"

# Better search terms for viral/meme-worthy reaction clips
MEME_SEARCH_TERMS = [
    "funny cat",
    "wait what",
    "shocked face",
    "laughing hysterically",
    "dog fail",
    "dancing monkey",
    "surprised pikachu",
    "oh my god",
    "mind blown",
    "awkward silence",
    "confused math lady",
    "evil laugh",
    "celebration dance",
    "facepalm",
    "no way",
    "dramatic chipmunk",
    "thug life",
    "wasted",
]

def download_vlipsy_memes(limit_per_term=3, total_target=50):
    """Search and download meme clips from Vlipsy."""
    os.makedirs(MEME_DIR, exist_ok=True)
    
    downloaded_count = 0
    
    # 1. First, try to get some "Trending" vlips
    logger.info("🔥 Fetching trending vlips...")
    try:
        resp = requests.get(
            f"{VLIPSY_API_BASE}/vlips/trending",
            params={"key": VLIPSY_API_KEY, "limit": 10},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            for vlip in data:
                if downloaded_count >= total_target:
                    break
                if download_vlip(vlip, "trending"):
                    downloaded_count += 1
    except Exception as e:
        logger.error(f"Error fetching trending: {e}")

    # 2. Search for specific reaction terms
    for term in MEME_SEARCH_TERMS:
        if downloaded_count >= total_target:
            break
            
        logger.info(f"🔍 Searching Vlipsy for: '{term}'...")
        try:
            resp = requests.get(
                f"{VLIPSY_API_BASE}/vlips/search",
                params={"q": term, "key": VLIPSY_API_KEY, "limit": limit_per_term},
                timeout=30
            )
            
            if resp.status_code != 200:
                logger.warning(f"Failed to search '{term}': {resp.status_code}")
                continue
                
            data = resp.json().get("data", [])
            for vlip in data:
                if downloaded_count >= total_target:
                    break
                if download_vlip(vlip, term):
                    downloaded_count += 1
                    
        except Exception as e:
            logger.error(f"Error searching '{term}': {e}")
            
    logger.success(f"🎉 Finished. Total new memes in pool: {downloaded_count}")

def download_vlip(vlip, term_tag):
    """Download a single vlip object."""
    vlip_id = vlip.get("id")
    title = vlip.get("title", "meme").replace(" ", "_")[:20]
    
    # Get the highest quality MP4 URL (prefer non-watermarked if available, but usually it's there)
    media = vlip.get("media", {})
    mp4 = media.get("mp4", {})
    url = mp4.get("url") or mp4.get("watermark")
    
    if not url:
        return False
        
    filename = f"vlipsy_{vlip_id}_{term_tag.replace(' ', '_')}_{title}.mp4"
    filepath = os.path.join(MEME_DIR, filename)
    
    if os.path.exists(filepath):
        # logger.debug(f"Skipping {filename}, already exists.")
        return True
        
    try:
        logger.info(f"  ⬇️  Downloading: {filename}")
        r = requests.get(url, timeout=60)
        with open(filepath, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        logger.error(f"  ❌ Failed to download {vlip_id}: {e}")
        return False

if __name__ == "__main__":
    download_vlipsy_memes()
