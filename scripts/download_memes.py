#!/usr/bin/env python3
"""
Download meme-style reaction clips from Pixabay for the meme-surprise video format.
These clips are royalty-free and will be used as surprise inserts in Shorts.
"""
import os
import sys
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MEME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resource", "memes")

# Search terms that yield funny/reaction/meme-worthy clips on Pixabay
MEME_SEARCH_TERMS = [
    "funny cat reaction",
    "surprised face",
    "dog funny",
    "baby laughing",
    "fail funny",
    "dance funny",
    "monkey funny",
    "parrot dancing",
    "cat jump fail",
    "surprised animal",
    "funny bird",
    "hamster funny",
    "penguin walking",
    "puppy playing",
    "owl surprised",
    "raccoon funny",
]

def download_meme_clips():
    """Download short meme clips from Pixabay."""
    api_key = os.environ.get("PIXABAY_API_KEY", "")
    if not api_key:
        # Try loading from config
        try:
            import toml
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.toml")
            if os.path.exists(config_path):
                cfg = toml.load(config_path)
                keys = cfg.get("app", {}).get("pixabay_api_keys", [])
                if keys:
                    api_key = keys[0]
        except Exception:
            pass
    
    if not api_key:
        print("ERROR: No PIXABAY_API_KEY found. Set it as environment variable or in config.toml")
        sys.exit(1)
    
    os.makedirs(MEME_DIR, exist_ok=True)
    
    downloaded = 0
    target = 30
    
    for term in MEME_SEARCH_TERMS:
        if downloaded >= target:
            break
            
        print(f"\n🔍 Searching: '{term}'...")
        
        params = {
            "key": api_key,
            "q": term,
            "video_type": "film",
            "per_page": 5,
            "safesearch": "true",
            "min_width": 720,
            "order": "popular",
        }
        
        try:
            resp = requests.get("https://pixabay.com/api/videos/", params=params, timeout=30)
            data = resp.json()
            
            hits = data.get("hits", [])
            for hit in hits:
                if downloaded >= target:
                    break
                
                # Get duration - prefer short clips (under 15 seconds)
                duration = hit.get("duration", 0)
                if duration > 15 or duration < 2:
                    continue
                
                # Get the medium quality video URL
                videos = hit.get("videos", {})
                medium = videos.get("medium", {}) or videos.get("small", {})
                url = medium.get("url", "")
                
                if not url:
                    continue
                
                vid_id = hit.get("id", downloaded)
                filename = f"meme_{downloaded:03d}_{term.replace(' ', '_')[:20]}_{vid_id}.mp4"
                filepath = os.path.join(MEME_DIR, filename)
                
                if os.path.exists(filepath):
                    print(f"  ⏭️  Already exists: {filename}")
                    downloaded += 1
                    continue
                
                print(f"  ⬇️  Downloading: {filename} ({duration}s)")
                video_resp = requests.get(url, timeout=60)
                with open(filepath, "wb") as f:
                    f.write(video_resp.content)
                
                downloaded += 1
                print(f"  ✅ Saved ({downloaded}/{target})")
                
        except Exception as e:
            print(f"  ❌ Error searching '{term}': {e}")
            continue
    
    print(f"\n🎉 Downloaded {downloaded} meme clips to {MEME_DIR}")
    
    # List what we have
    clips = [f for f in os.listdir(MEME_DIR) if f.endswith(".mp4")]
    print(f"📁 Total meme clips available: {len(clips)}")


if __name__ == "__main__":
    download_meme_clips()
