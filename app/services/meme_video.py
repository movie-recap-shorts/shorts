#!/usr/bin/env python3
"""
Meme-Surprise Video Generator

Generates YouTube Shorts in the format:
    [Topic Hook Clip 5-10s] → [Surprise Meme Clip 3-8s] → [Like & Subscribe Outro 3-5s]

This module bypasses the standard LLM script pipeline and directly assembles
pre-made segments using MoviePy.
"""
import glob
import math
import os
import random
import uuid
from os import path
from typing import Optional, Dict, Any, List, Tuple

from loguru import logger
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

from app.config import config
from app.models.schema import VideoAspect
from app.services import llm, material, voice
from app.utils import utils


# Paths
PROJECT_ROOT = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
MEME_DIR = path.join(PROJECT_ROOT, "resource", "memes")
OUTRO_DIR = path.join(PROJECT_ROOT, "resource", "outros")
FONTS_DIR = path.join(PROJECT_ROOT, "resource", "fonts")


def get_font_path() -> str:
    """Get a font path that works on both macOS and Linux (GitHub Actions)."""
    # 1. Bundled font (always shipped with repo)
    bundled = path.join(FONTS_DIR, "Charm-Bold.ttf")
    if os.path.exists(bundled):
        return bundled
    
    # 2. Ubuntu / Debian DejaVu (GitHub Actions runners)
    dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(dejavu):
        return dejavu
    
    # 3. macOS system font
    mac_font = "/System/Library/Fonts/Helvetica.ttc"
    if os.path.exists(mac_font):
        return mac_font
    
    # 4. Last resort — let Pillow try to find something
    return "DejaVuSans-Bold"


# Premium Color Palette for text randomization
PREMIUM_COLORS = [
    "#FFFFFF",  # White
    "#F0F0F0",  # Off-white
    "#FFFDD0",  # Cream
    "#FFD700",  # Gold (subtle)
    "#E6E6FA",  # Lavender
    "#F5F5DC",  # Beige
    "#F0FFF0",  # Honeydew
]

# Hook text templates per channel type
HOOK_TEMPLATES = {
    "movies_en": [
        "Wait for it... this scene is insane!",
        "You won't believe what happens next...",
        "This movie scene will blow your mind!",
        "Watch this... I wasn't ready!",
        "No way this actually happened in a movie!",
        "This is the craziest scene ever filmed!",
        "Hold on... watch till the end!",
        "This scene gave me chills!",
        "I can't stop watching this part!",
        "The twist nobody saw coming!",
    ],
    "motivation_en": [
        "Remember this when life gets tough...",
        "This changed my entire mindset!",
        "Watch this if you need motivation today...",
        "The secret to success in one sentence...",
        "Winners think differently... watch this!",
        "This is why most people give up...",
        "Stop scrolling and listen to this!",
        "The truth about success nobody tells you...",
        "This mindset shift changes everything!",
        "One thought that can change your life...",
    ],
    "finance_en": [
        "This money secret feels illegal to know...",
        "Stop saving money, do this instead!",
        "Warren Buffett's number one rule is...",
        "How to retire with a million dollars...",
        "The rich don't work for money, they...",
        "One habit that makes you poor...",
        "This is why you're not rich yet!",
        "Passive income is easier than you think...",
        "The fastest way to double your money...",
        "Bankers don't want you to know this!",
    ],
    "tech_en": [
        "This AI tool is actually scary...",
        "Your phone is listening to you...",
        "The future of the internet is here...",
        "Stop using Google, use this instead!",
        "This website feels illegal to know!",
        "Productivity hack that saves hours...",
        "The dark side of AI explained...",
        "You won't believe this tech exists!",
        "One click to automate your life...",
        "This gadget replaces your laptop!",
    ],
    "scary_en": [
        "This will keep you up at night...",
        "Listen to this 911 call carefully...",
        "The dark web is worse than you think...",
        "You're not alone in your room...",
        "This true story gave me chills!",
        "The scariest thing caught on camera...",
        "Never google this term at night...",
        "This photo has a terrifying secret...",
        "The most haunted place on Earth...",
        "Don't look behind you right now!",
    ],
}


def get_random_meme_clip() -> Optional[str]:
    """Pick a random meme clip from the library."""
    if not os.path.exists(MEME_DIR):
        logger.error(f"Meme directory not found: {MEME_DIR}")
        return None
    
    clips = glob.glob(os.path.join(MEME_DIR, "*.mp4"))
    if not clips:
        logger.error("No meme clips found in library")
        return None
    
    chosen = random.choice(clips)
    logger.info(f"🎭 Selected meme: {os.path.basename(chosen)}")
    return chosen


def get_random_outro() -> Optional[str]:
    """Pick a random outro audio clip."""
    if not os.path.exists(OUTRO_DIR):
        logger.error(f"Outro directory not found: {OUTRO_DIR}")
        return None
    
    clips = glob.glob(os.path.join(OUTRO_DIR, "*.mp3"))
    if not clips:
        logger.error("No outro audio clips found")
        return None
    
    return random.choice(clips)


def get_hook_text(channel_name: str) -> str:
    """Get a random hook text for the given channel type."""
    templates = HOOK_TEMPLATES.get(channel_name, HOOK_TEMPLATES["movies_en"])
    return random.choice(templates)


def download_topic_clip(
    task_id: str,
    search_term: str,
    target_duration: float = 7.0,
    video_aspect: str = "9:16",
) -> Optional[str]:
    """Download a single topic-related clip from Pixabay/Pexels."""
    logger.info(f"🎬 Downloading topic clip for: '{search_term}'")
    
    source = config.app.get("video_source", "pixabay")
    
    # Ensure search_term is a string
    if isinstance(search_term, list):
        search_term = " ".join(search_term)
    
    downloaded = material.download_videos(
        task_id=task_id,
        search_terms=[search_term],
        source=source,
        video_aspect=VideoAspect(video_aspect),
        audio_duration=target_duration * 2,  # Download extra to have options
        max_clip_duration=int(target_duration),
    )
    
    if not downloaded:
        logger.warning(f"No clips found for '{search_term}', trying generic terms")
        fallback_terms = ["cinematic scene", "epic moment", "dramatic scene", "nature scenery"]
        for term in fallback_terms:
            downloaded = material.download_videos(
                task_id=task_id,
                search_terms=[term],
                source=source,
                video_aspect=VideoAspect(video_aspect),
                audio_duration=target_duration * 2,
                max_clip_duration=int(target_duration),
            )
            if downloaded:
                break
    
    if downloaded:
        return downloaded[0]
    return None


async def generate_hook_audio(text: str, task_dir: str, voice_name: str = "en-US-GuyNeural") -> Tuple[Optional[str], float]:
    """Generate TTS audio for the hook text."""
    audio_file = path.join(task_dir, "hook_audio.mp3")
    
    sub_maker = voice.tts(
        text=text,
        voice_name=voice_name,
        voice_rate=1.0,
        voice_file=audio_file,
    )
    
    if not os.path.exists(audio_file):
        logger.error("Failed to generate hook audio")
        return None, 0
    
    duration = voice.get_audio_duration(audio_file)
    if duration == 0:
        # Try getting from sub_maker
        if sub_maker:
            duration = math.ceil(voice.get_audio_duration(sub_maker))
    
    logger.info(f"🎙️ Hook audio generated: {duration:.1f}s")
    return audio_file, duration


def resize_clip_to_aspect(clip, target_width: int, target_height: int):
    """Resize a clip to fit the target aspect ratio with black bars if needed."""
    clip_w, clip_h = clip.size
    
    if clip_w == target_width and clip_h == target_height:
        return clip
    
    clip_ratio = clip_w / clip_h
    video_ratio = target_width / target_height
    
    if clip_ratio == video_ratio:
        return clip.resized(new_size=(target_width, target_height))
    
    # Scale to fit within bounds
    if clip_ratio > video_ratio:
        scale_factor = target_width / clip_w
    else:
        scale_factor = target_height / clip_h
    
    new_width = int(clip_w * scale_factor)
    new_height = int(clip_h * scale_factor)
    
    background = ColorClip(
        size=(target_width, target_height), color=(0, 0, 0)
    ).with_duration(clip.duration)
    
    clip_resized = clip.resized(new_size=(new_width, new_height)).with_position("center")
    return CompositeVideoClip([background, clip_resized])


def create_outro_video(
    outro_audio_path: str,
    target_width: int = 1080,
    target_height: int = 1920,
    output_path: str = "",
) -> Optional[str]:
    """Create an outro video segment with audio and animated text."""
    try:
        audio = AudioFileClip(outro_audio_path)
        duration = audio.duration + 0.5  # Add small padding
        
        # Dark gradient background
        bg = ColorClip(
            size=(target_width, target_height),
            color=(15, 15, 25),
        ).with_duration(duration)
        
        # "Like & Subscribe" text
        font_path = get_font_path()
        try:
            txt = TextClip(
                text="LIKE & SUBSCRIBE!",
                font_size=55,
                color="white",
                font=font_path,
                stroke_color="black",
                stroke_width=2,
            ).with_duration(duration).with_position("center")
        except Exception:
            # Fallback
            txt = TextClip(
                text="LIKE & SUBSCRIBE!",
                font_size=55,
                color="white",
                font=font_path,
                stroke_color="black",
                stroke_width=2,
            ).with_duration(duration).with_position("center")
        
        outro_clip = CompositeVideoClip([bg, txt]).with_audio(audio)
        
        if output_path:
            outro_clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )
            outro_clip.close()
            audio.close()
            return output_path
        
        return outro_clip
        
    except Exception as e:
        logger.error(f"Failed to create outro video: {e}")
        return None


def generate_meme_short(
    task_id: str,
    channel_name: str,
    channel_config: Dict[str, Any],
    topic: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate a meme-surprise short video.
    
    Pipeline:
    1. Pick random topic & generate hook text
    2. Download topic-related clip from Pixabay (5-10s)
    3. Generate TTS hook text as audio overlay
    4. Pick random meme clip from resource/memes/
    5. Create outro segment with "like & subscribe" audio
    6. Concatenate: [hook+topic clip] → [meme] → [outro]
    
    Returns:
        Dictionary with video path and metadata, or None on failure.
    """
    logger.info(f"🎬 Starting meme-surprise video generation for {channel_name}")
    
    # Setup task directory
    task_dir = utils.task_dir(task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    aspect = VideoAspect(channel_config.get("video_aspect", "9:16"))
    video_width, video_height = aspect.to_resolution()
    voice_name = channel_config.get("voice", "en-US-GuyNeural-Male")
    # Parse voice name for edge-tts (remove gender suffix)
    voice_name_clean = voice_name.rsplit("-", 1)[0] if "-Male" in voice_name or "-Female" in voice_name else voice_name
    
    # 1. Select topic and hook text
    if not topic:
        topics = channel_config.get("topics", [])
        topic = random.choice(topics) if topics else "amazing viral moment"
    
    # Generate a viral hook using AI (DeepSeek)
    language = channel_config.get("language", "en")
    
    # Concept-specific script generation
    if "motivation" in channel_name:
        hook_text = llm.generate_stoic_script(topic=topic, language=language)
    elif "movie" in channel_name:
        hook_text = llm.generate_movie_secret_script(topic=topic, language=language)
    else:
        hook_text = llm.generate_viral_hook(topic=topic, language=language)
    
    logger.info(f"📝 Topic: {topic}")
    logger.info(f"📝 AI Hook: {hook_text}")
    
    # 2. Generate hook audio (TTS)
    logger.info("🎙️ Generating hook audio...")
    hook_audio_path = path.join(task_dir, "hook_audio.mp3")
    sub_maker = voice.tts(
        text=hook_text,
        voice_name=voice.parse_voice_name(voice_name),
        voice_rate=1.0,
        voice_file=hook_audio_path,
    )
    
    if not os.path.exists(hook_audio_path):
        logger.error("Failed to generate hook audio")
        return None
    
    hook_audio = AudioFileClip(hook_audio_path)
    hook_duration = hook_audio.duration
    logger.info(f"🎙️ Hook audio duration: {hook_duration:.1f}s")
    
    # Ensure hook is between 3-10 seconds
    target_hook_duration = max(3.0, min(10.0, hook_duration + 1.0))
    
    # 3. Download topic clip
    logger.info("🎬 Downloading topic clip...")
    # Use first 4 words of topic as search term
    search_words = " ".join(topic.split()[:4]) if isinstance(topic, str) else str(topic)
    topic_clip_path = download_topic_clip(
        task_id=task_id,
        search_term=search_words,
        target_duration=target_hook_duration,
        video_aspect=channel_config.get("video_aspect", "9:16"),
    )
    
    if not topic_clip_path:
        logger.error("Failed to download topic clip")
        hook_audio.close()
        return None
    
    # 4. Get random meme clip
    meme_path = get_random_meme_clip()
    if not meme_path:
        logger.error("No meme clips available")
        hook_audio.close()
        return None
    
    # 5. Get outro audio
    outro_audio_path = get_random_outro()
    if not outro_audio_path:
        logger.error("No outro audio available")
        hook_audio.close()
        return None
    
    # 6. Assemble the video
    logger.info("🔧 Assembling meme-surprise video...")
    
    try:
        # --- SEGMENT 1: Topic clip with hook audio ---
        topic_clip = VideoFileClip(topic_clip_path)
        
        # Trim topic clip to target duration
        if topic_clip.duration > target_hook_duration:
            topic_clip = topic_clip.subclipped(0, target_hook_duration)
        elif topic_clip.duration < 3.0:
            # If too short, loop it
            loops = math.ceil(target_hook_duration / topic_clip.duration)
            clips_to_concat = [topic_clip] * loops
            topic_clip = concatenate_videoclips(clips_to_concat)
            topic_clip = topic_clip.subclipped(0, target_hook_duration)
        
        topic_clip = resize_clip_to_aspect(topic_clip, video_width, video_height)
        
        # Add hook audio overlay
        hook_audio_padded = hook_audio
        if hook_audio.duration < topic_clip.duration:
            # Audio is shorter than video - that's fine, video continues silently
            pass
        
        # RCP (Reuse Content Protection): Randomize text appearance
        font_path = get_font_path()
        text_color = random.choice(PREMIUM_COLORS)
        text_size = random.randint(48, 54)  # Slight variation
        
        try:
            hook_subtitle = TextClip(
                text=hook_text,
                font_size=text_size,
                color=text_color,
                font=font_path,
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(video_width - 100, None),
                text_align="center",
            ).with_duration(min(hook_audio.duration + 0.5, topic_clip.duration)).with_position(("center", video_height * 0.4))
        except Exception as e:
            logger.warning(f"Subtitle creation failed, trying fallback: {e}")
            hook_subtitle = TextClip(
                text=hook_text,
                font_size=text_size - 5,
                color=text_color,
                font=font_path,
                stroke_color="black",
                stroke_width=2,
            ).with_duration(min(hook_audio.duration + 0.5, topic_clip.duration)).with_position("center")
        
        # RCP (Reuse Content Protection): Random Zoom on topic clip
        zoom_factor = random.uniform(1.0, 1.08)
        if zoom_factor > 1.01:
            topic_clip = topic_clip.resized(zoom_factor)
            # Re-center if zoomed
            w_diff = (topic_clip.w - video_width) / 2
            h_diff = (topic_clip.h - video_height) / 2
            topic_clip = topic_clip.cropped(x1=w_diff, y1=h_diff, x2=topic_clip.w-w_diff, y2=topic_clip.h-h_diff)
        
        segment1 = CompositeVideoClip([topic_clip, hook_subtitle])
        
        # RCP: Subtle audio volume variation
        audio_volume = random.uniform(0.95, 1.05)
        segment1 = segment1.with_audio(hook_audio_padded.with_volume_scaled(audio_volume))
        
        # --- SEGMENT 2: Meme clip (with its own audio) ---
        meme_clip = VideoFileClip(meme_path)
        
        # Trim meme to 3-8 seconds
        meme_max_dur = min(8.0, meme_clip.duration)
        meme_start = 0
        if meme_clip.duration > 8:
            meme_start = random.uniform(0, meme_clip.duration - 8)
        meme_clip = meme_clip.subclipped(meme_start, meme_start + meme_max_dur)
        meme_clip = resize_clip_to_aspect(meme_clip, video_width, video_height)
        
        # Audio Copyright Protection: Lower meme clip volume significantly
        if meme_clip.audio is not None:
            meme_clip = meme_clip.with_audio(meme_clip.audio.with_effects([afx.MultiplyVolume(0.2)]))
            
        segment2 = meme_clip
        
        # --- SEGMENT 3: Outro ---
        outro_audio = AudioFileClip(outro_audio_path)
        # Cap outro duration to 1.5 seconds max to prevent swipe-aways (AVD killer)
        outro_duration = min(1.5, outro_audio.duration + 0.5)
        
        outro_bg = ColorClip(
            size=(video_width, video_height),
            color=(15, 15, 25),
        ).with_duration(outro_duration)
        
        try:
            outro_text = TextClip(
                text="LIKE & SUBSCRIBE!",
                font_size=55,
                color="white",
                font=font_path,
                stroke_color="black",
                stroke_width=2,
                text_align="center",
            ).with_duration(outro_duration).with_position("center")
        except Exception:
            outro_text = TextClip(
                text="LIKE & SUBSCRIBE!",
                font_size=55,
                color="white",
                font=font_path,
                stroke_color="black",
                stroke_width=2,
            ).with_duration(outro_duration).with_position("center")
        
        segment3 = CompositeVideoClip([outro_bg, outro_text]).with_audio(outro_audio)
        
        # --- CONCATENATE ALL SEGMENTS ---
        logger.info(f"📐 Segment durations: Hook={segment1.duration:.1f}s, Meme={segment2.duration:.1f}s, Outro={segment3.duration:.1f}s")
        
        final = concatenate_videoclips([segment1, segment2, segment3], method="compose")
        
        total_duration = final.duration
        logger.info(f"📐 Total video duration: {total_duration:.1f}s")
        
        # Write final video
        output_path = path.join(task_dir, "final-1.mp4")
        logger.info(f"💾 Writing final video to: {output_path}")
        
        final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            logger=None,
        )
        
        # Cleanup
        for clip in [topic_clip, meme_clip, hook_audio, outro_audio, segment1, segment2, segment3, final]:
            try:
                clip.close()
            except Exception:
                pass
        
        if hook_subtitle:
            try:
                hook_subtitle.close()
            except Exception:
                pass
        
        logger.success(f"✅ Meme-surprise video generated: {output_path} ({total_duration:.1f}s)")
        
        return {
            "videos": [output_path],
            "script": hook_text,
            "topic": topic,
            "meme": os.path.basename(meme_path),
            "duration": total_duration,
        }
        
    except Exception as e:
        logger.error(f"Failed to assemble meme-surprise video: {e}")
        import traceback
        traceback.print_exc()
        return None
