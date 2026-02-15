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

# Better search terms for viral/meme-worthy reaction clips (including dark humor/funny)
MEME_SEARCH_TERMS = [
    "dark humor funny",
    "funny reaction memes",
    "shocking surprise",
    "wait for it funny",
    "unexpected ending",
    "funny cat fail",
    "laughing hysterically",
    "cursed images video",
    "awkward silence funny",
    "confused meme",
    "evil laugh funny",
    "savage reaction",
    "instant regret",
    "karma funny",
    "scary jump scare funny",
    "funny pranks",
    "mind blown reaction",
    "celebration dance funny",
    "facepalm funny",
    "no way meme",
    "dramatic reaction",
    "thug life funny",
    "wasted meme",
    "black humor clips",
    "unusual videos funny",
    "offensive memes funny", 
    "meme clips 2024",
    "funny movie scenes",
    "cartoon funny reaction",
    "sigma male meme",
    "gigachad funny",
    "cursed meme videos",
    "darkest humor clips",
    "unexpected karma",
    "funny fail compilation",
]

def download_vlipsy_memes(limit_per_term=10, total_target=130):
    """Search and download meme clips from Vlipsy."""
    os.makedirs(MEME_DIR, exist_ok=True)
    
    downloaded_count = 0
    
    # 1. First, try to get some "Trending" vlips
    logger.info("🔥 Fetching trending vlips...")
    try:
        resp = requests.get(
            f"{VLIPSY_API_BASE}/vlips/trending",
            params={"key": VLIPSY_API_KEY, "limit": 20},
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
            
    logger.success(f"🎉 Finished. Total memes in pool: {downloaded_count}")

def download_vlip(vlip, term_tag):
    """Download a single vlip object."""
    vlip_id = vlip.get("id")
    title = vlip.get("title", "meme").replace(" ", "_")[:20]
    
    # Check duration (Vlipsy API might not always return duration in search, 
    # but we can check if it exists)
    # The user wants > 5 seconds
    duration = float(vlip.get("duration", 0) or 0)
    # If duration is 0, we'll download anyway as many vlips are usually 5-15s
    if duration > 0 and duration < 5:
        # logger.debug(f"Skipping {vlip_id}, too short ({duration}s)")
        return False
        
    # Get the highest quality MP4 URL
    media = vlip.get("media", {})
    mp4 = media.get("mp4", {})
    url = mp4.get("url") or mp4.get("watermark")
    
    if not url:
        return False
        
    filename = f"vlipsy_{vlip_id}_{term_tag.replace(' ', '_')}_{title}.mp4"
    filepath = os.path.join(MEME_DIR, filename)
    
    if os.path.exists(filepath):
        return True
        
    try:
        logger.info(f"  ⬇️  Downloading: {filename}")
        r = requests.get(url, timeout=60)
        with open(filepath, "wb") as f:
            f.write(r.content)
        
        # After download, check real duration if possible (optional but good)
        return True
    except Exception as e:
        logger.error(f"  ❌ Failed to download {vlip_id}: {e}")
        return False

if __name__ == "__main__":
    download_vlipsy_memes()
