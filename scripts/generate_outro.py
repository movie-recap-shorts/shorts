#!/usr/bin/env python3
"""
Generate the outro audio clip (TTS) for the meme-surprise video format.
Creates a "Like and Subscribe" audio file using edge-tts.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTRO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resource", "outros")

OUTRO_TEXTS = [
    "Like and subscribe for more!",
    "Smash that like button and subscribe!",
    "If you enjoyed this, hit like and subscribe!",
    "Don't forget to like and subscribe!",
]

async def generate_outro_audio():
    """Generate outro audio clips using edge-tts."""
    try:
        import edge_tts
    except ImportError:
        print("Installing edge-tts...")
        os.system(f"{sys.executable} -m pip install edge-tts")
        import edge_tts
    
    os.makedirs(OUTRO_DIR, exist_ok=True)
    
    voice = "en-US-GuyNeural"
    
    for i, text in enumerate(OUTRO_TEXTS):
        filename = f"outro_{i:02d}.mp3"
        filepath = os.path.join(OUTRO_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"⏭️  Already exists: {filename}")
            continue
        
        print(f"🎙️ Generating: '{text}' -> {filename}")
        
        communicate = edge_tts.Communicate(text, voice, rate="+10%")
        await communicate.save(filepath)
        
        print(f"✅ Saved: {filepath}")
    
    print(f"\n🎉 Outro audio files ready in {OUTRO_DIR}")
    clips = [f for f in os.listdir(OUTRO_DIR) if f.endswith(".mp3")]
    print(f"📁 Total outro clips: {len(clips)}")


if __name__ == "__main__":
    asyncio.run(generate_outro_audio())
