#!/usr/bin/env python3
"""
YouTube Shorts Automation System

Main entry point for the multi-channel YouTube Shorts automation.
Supports both scheduled mode (continuous) and one-shot mode.

Usage:
    # Start scheduler for all channels
    python automation.py --mode scheduler
    
    # Generate and upload one video for a specific channel
    python automation.py --once --channel motivation_tr
    
    # Dry run (generate video but don't upload)
    python automation.py --once --channel motivation_tr --dry-run
    
    # List configured channels
    python automation.py --list-channels
"""

import argparse
import random
import sys
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.channel_manager import ChannelManager, create_sample_config
from app.services.scheduler import ShortsScheduler
from app.services.youtube_uploader import YouTubeUploader
from app.services import task as video_task, llm
from app.services.meme_video import generate_meme_short
from app.services.instagram_uploader_v2 import upload_to_instagram_browser
from app.services.tiktok_uploader_v2 import upload_to_tiktok_browser
from app.models.schema import VideoParams


# Configuration paths
CONFIG_DIR = project_root / "config"
CREDENTIALS_DIR = project_root / "credentials"
CHANNELS_CONFIG = CONFIG_DIR / "channels.json"


def setup_logging():
    """Configure logging for the automation system."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/automation_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG"
    )


def generate_meme_and_upload(
    channel_name: str,
    channel_manager: ChannelManager,
    topic: Optional[str] = None,
    dry_run: bool = False,
    ignore_interval: bool = False,
    ignore_schedule: bool = False
) -> bool:
    """
    Generate a meme-surprise video and upload it to YouTube.
    Uses the 3-segment format: [topic hook] → [meme clip] → [outro]
    """
    logger.info(f"Starting MEME video generation for channel: {channel_name}")
    
    # Check rate limits
    if not dry_run and not channel_manager.can_upload(
        channel_name, 
        ignore_interval=ignore_interval,
        ignore_schedule=ignore_schedule
    ):
        logger.info(f"Upload criteria not met for {channel_name}, skipping.")
        return None
    
    # Get channel config
    channel = channel_manager.get_channel(channel_name)
    if not channel:
        logger.error(f"Channel not found: {channel_name}")
        return False
    
    # Select topic using smart history logic
    if not topic:
        topic = channel_manager.get_random_topic(channel_name)
    
    if not topic:
        logger.error(f"No topics configured for channel: {channel_name}")
        return False

    # Build channel config dict for meme_video module
    channel_config = {
        "topics": channel.topics,
        "voice": channel.voice,
        "video_aspect": channel.video_aspect,
        "tags": channel.tags,
    }

    task_id = str(uuid.uuid4())
    
    try:
        result = generate_meme_short(
            task_id=task_id,
            channel_name=channel_name,
            channel_config=channel_config,
            topic=topic,
        )
        
        if not result or not result.get('videos'):
            logger.error(f"Meme video generation failed for {channel_name}")
            return False
        
        video_path = result['videos'][0]
        hook_text = result.get('script', '')
        topic_used = result.get('topic', '')
        
        logger.success(f"Meme video generated: {video_path} ({result.get('duration', 0):.1f}s)")
        
        # AI-Generated Viral Title (DeepSeek)
        title = llm.generate_viral_title(
            topic=topic_used, 
            hook_text=hook_text, 
            language=channel.language
        )
        
        logger.info(f"🏷️ AI Title: {title}")

        if dry_run:
            logger.info("Dry run mode - skipping upload")
            return True
        
        # Get relevant affiliate link
        affiliate_link = channel_manager.get_affiliate_link(channel_name, hook_text)
        
        # Use safe replacement for description template
        raw_description = channel.description_template.replace("{script_summary}", hook_text)
        description = raw_description.replace("{{relevant_affiliate_link}}", affiliate_link)
        
        # Get uploader and authenticate
        uploader = channel_manager.get_uploader(channel_name)
        if not uploader:
            logger.error(f"Failed to get uploader for {channel_name}")
            return False
        
        if not uploader.authenticate(interactive=False):
            logger.error(f"Authentication failed for {channel_name}")
            return False
        
        # Upload video
        upload_result = uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=channel.tags,
            privacy_status=channel.default_privacy,
            is_shorts=True,
            notify_subscribers=channel.notify_subscribers
        )
        
        if upload_result:
            video_id = upload_result.get('id')
            logger.success(f"Meme video uploaded! ID: {video_id}")
            logger.info(f"URL: https://youtube.com/watch?v={video_id}")
            
            # Record upload for rate limiting
            channel_manager.record_upload(channel_name)
            
            # --- CROSS-PLATFORM UPLOAD (TikTok & Instagram) ---
            channel_config = channel_manager.get_channel(channel_name)
            
            if channel_config.enable_instagram:
                # Method 3: Browser-based upload (Resilient to IP blocks)
                from app.services.instagram_uploader_v2 import upload_to_instagram_browser
                logger.info(f"Uploading to Instagram Reels (Browser Mode) for {channel_name}...")
                
                try:
                    ig_result = upload_to_instagram_browser(
                        video_path=video_path,
                        caption=f"{title}\n\n{description}",
                        channel_name=channel_name,
                        credentials_dir=str(CREDENTIALS_DIR)
                    )
                    if ig_result:
                        logger.success(f"Instagram Reels upload successful via browser!")
                except Exception as e:
                    logger.warning(f"Instagram browser upload failed (Soft Fail): {e}")
                    logger.info("Continuing execution despite Instagram error...")
                    
            if channel_config.enable_tiktok:
                # Method 3: Browser-based upload (handles modals and avoids asyncio loop issues)
                from app.services.tiktok_uploader_v2 import upload_to_tiktok_browser
                logger.info(f"Uploading to TikTok (Browser Mode) for {channel_name}...")
                
                try:
                    tt_result = upload_to_tiktok_browser(
                        video_path=video_path,
                        description=title, # TikTok usually prefers shorter captions (titles)
                        channel_name=channel_name,
                        credentials_dir=str(CREDENTIALS_DIR)
                    )
                    if tt_result:
                        logger.success(f"TikTok upload successful via browser!")
                except Exception as e:
                    logger.warning(f"TikTok browser upload failed: {e}")
            
            return True
        else:
            logger.error(f"Upload failed for {channel_name}")
            return False
            
    except Exception as e:
        logger.exception(f"Error during meme generation/upload: {e}")
        return False


def generate_and_upload(
    channel_name: str,
    channel_manager: ChannelManager,
    topic: Optional[str] = None,
    dry_run: bool = False,
    ignore_interval: bool = False,
    ignore_schedule: bool = False
) -> bool:
    """
    Generate a video and upload it to YouTube.
    
    Args:
        channel_name: Name of the channel
        channel_manager: ChannelManager instance
        topic: Optional specific topic (random if not provided)
        dry_run: If True, skip upload step
        
    Returns:
        True if successful
    """
    logger.info(f"Starting video generation for channel: {channel_name}")
    
    # Check rate limits
    if not dry_run and not channel_manager.can_upload(
        channel_name, 
        ignore_interval=ignore_interval,
        ignore_schedule=ignore_schedule
    ):
        logger.info(f"Upload criteria not met for {channel_name}, skipping.")
        return None
    
    # Get channel config
    channel = channel_manager.get_channel(channel_name)
    if not channel:
        logger.error(f"Channel not found: {channel_name}")
        return False
    
    # Get video parameters
    video_params = channel_manager.get_video_params(channel_name, topic)
    if not video_params:
        logger.error(f"Failed to get video parameters for {channel_name}")
        return False
    
    # Create unique task ID
    task_id = str(uuid.uuid4())
    
    logger.info(f"Generating video with topic: {video_params['video_subject']}")
    
    try:
        # Create VideoParams object
        params = VideoParams(
            video_subject=video_params['video_subject'],
            video_language=video_params['video_language'],
            voice_name=video_params['voice_name'],
            video_aspect=video_params['video_aspect'],
            video_clip_duration=video_params['video_clip_duration'],
            paragraph_number=video_params['paragraph_number'],
            subtitle_enabled=video_params['subtitle_enabled'],
            subtitle_position=video_params.get('subtitle_position', 'top'),
            video_count=1,
        )
        
        # Generate video
        result = video_task.start(task_id, params)
        
        if not result or not result.get('videos'):
            logger.error(f"Video generation failed for {channel_name}")
            return False
        
        video_path = result['videos'][0]
        video_script = result.get('script', '')
        
        logger.success(f"Video generated: {video_path}")
        
        if dry_run:
            logger.info("Dry run mode - skipping upload")
            return True
        
        # Prepare upload metadata with enhanced title
        def enhance_title(base_title: str) -> str:
            """Make titles more clickable with emojis and power words"""
            emoji_map = {
                'sci fi': '🚀',
                'science fiction': '🚀',
                'apocalyptic': '🌍',
                'zombie': '🧟',
                'thriller': '😱',
                'psychological': '🧠',
                'mind': '🤯',
                'conspiracy': '🕵️',
                'action': '💥',
                'cop': '👮',
                'heist': '💰',
                'revenge': '⚔️',
                'prison': '🔒',
                'chase': '🏃',
                'disaster': '🔥',
                'monster': '👹',
                'survival': '⛺',
                'space': '🌌',
                'parallel': '🌀',
                'motivation': '💪',
                'success': '🎯',
                'mindset': '🧠',
                'billionaire': '💰',
                'winner': '🏆',
                'confidence': '💎',
                'discipline': '⚡',
            }
            
            # Find relevant emoji
            title_lower = base_title.lower()
            emoji = ''
            for keyword, icon in emoji_map.items():
                if keyword in title_lower:
                    emoji = icon + ' '
                    break
            
            # Capitalize important words for better readability
            enhanced = base_title.title()
            
            return f"{emoji}{enhanced} #Shorts"[:100]
        
        title = enhance_title(video_params['video_subject'])
        
        # Create description from script
        script_summary = video_script[:500] if video_script else ""
        # Get relevant affiliate link
        affiliate_link = channel_manager.get_affiliate_link(channel_name, script_text)
        
        # Use safe replacement for description template
        raw_description = channel.description_template.replace("{script_summary}", script_summary)
        description = raw_description.replace("{{relevant_affiliate_link}}", affiliate_link)
        
        # Get uploader and authenticate
        uploader = channel_manager.get_uploader(channel_name)
        if not uploader:
            logger.error(f"Failed to get uploader for {channel_name}")
            return False
        
        if not uploader.authenticate(interactive=False):
            logger.error(f"Authentication failed for {channel_name}")
            return False
        
        # Upload video
        upload_result = uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=channel.tags,
            privacy_status=channel.default_privacy,
            is_shorts=True,
            notify_subscribers=channel.notify_subscribers
        )
        
        if upload_result:
            video_id = upload_result.get('id')
            logger.success(f"YouTube upload successful! ID: {video_id}")
            logger.info(f"URL: https://youtube.com/watch?v={video_id}")
            
            # Record upload for rate limiting
            channel_manager.record_upload(channel_name)
            
            # --- CROSS-PLATFORM UPLOAD (TikTok & Instagram) ---
            channel_config = channel_manager.get_channel(channel_name)
            
            if channel_config.enable_instagram:
                logger.info(f"Uploading to Instagram Reels (Browser Mode) for {channel_name}...")
                try:
                    ig_result = upload_to_instagram_browser(
                        video_path=video_path,
                        caption=f"{title}\n\n{description}",
                        channel_name=channel_name,
                        credentials_dir=str(CREDENTIALS_DIR)
                    )
                    if ig_result:
                        logger.success(f"Instagram Reels upload successful via browser!")
                except Exception as e:
                    logger.warning(f"Instagram browser upload failed (Soft Fail): {e}")
                    logger.info("Continuing execution despite Instagram error...")
                    
            if channel_config.enable_tiktok:
                logger.info(f"Uploading to TikTok (Browser Mode) for {channel_name}...")
                try:
                    tt_result = upload_to_tiktok_browser(
                        video_path=video_path,
                        description=title,
                        channel_name=channel_name,
                        credentials_dir=str(CREDENTIALS_DIR)
                    )
                    if tt_result:
                        logger.success(f"TikTok upload successful via browser!")
                except Exception as e:
                    logger.warning(f"TikTok browser upload failed (Soft Fail): {e}")
            
            return True
        else:
            logger.error(f"Upload failed for {channel_name}")
            return False
            
    except Exception as e:
        logger.exception(f"Error during generation/upload: {e}")
        return False


def run_scheduler(channel_manager: ChannelManager, dry_run: bool = False):
    """
    Run the scheduler for all configured channels.
    
    Args:
        channel_manager: ChannelManager instance
        dry_run: If True, skip uploads
    """
    scheduler = ShortsScheduler(timezone="Europe/Istanbul", blocking=True)
    
    # Add jobs for each channel
    for channel_name in channel_manager.list_channels():
        channel = channel_manager.get_channel(channel_name)
        if not channel:
            continue
        
        logger.info(f"Adding schedule for {channel_name}: {channel.schedule}")
        
        scheduler.add_channel_job(
            channel_name=channel_name,
            schedule=channel.schedule,
            job_func=generate_and_upload,
            channel_manager=channel_manager,
            dry_run=dry_run
        )
    
    if not scheduler.list_jobs():
        logger.error("No jobs scheduled. Check channel configuration.")
        return
    
    logger.info("Starting scheduler...")
    scheduler.start()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="YouTube Shorts Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--mode', 
        choices=['scheduler', 'once'],
        default='once',
        help='Run mode: scheduler (continuous) or once (single video)'
    )
    
    parser.add_argument(
        '--video-mode',
        choices=['standard', 'meme'],
        default='meme',
        help='Video format: standard (LLM script) or meme (meme-surprise format)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Generate and upload one video (shortcut for --mode once)'
    )
    
    parser.add_argument(
        '--channel',
        type=str,
        help='Channel name for one-shot mode'
    )
    
    parser.add_argument(
        '--topic',
        type=str,
        help='Specific topic for video generation'
    )
    
    parser.add_argument(
        '--catchup',
        action='store_true',
        help='Enable catch-up mode for missed slots'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=1,
        help='Maximum number of catch-up videos to generate (default: 1)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate video but do not upload'
    )
    
    parser.add_argument(
        '--ignore-schedule',
        action='store_true',
        help='Ignore channel schedule and upload immediately'
    )
    
    parser.add_argument(
        '--list-channels',
        action='store_true',
        help='List all configured channels'
    )
    
    parser.add_argument(
        '--create-sample-config',
        action='store_true',
        help='Create sample channel configuration'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=str(CHANNELS_CONFIG),
        help='Path to channels configuration file'
    )
    
    parser.add_argument(
        '--credentials-dir',
        type=str,
        default=str(CREDENTIALS_DIR),
        help='Path to credentials directory'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Create sample config if requested
    if args.create_sample_config:
        create_sample_config(args.config)
        logger.info("Sample configuration created. Please edit and add your channels.")
        return
    
    # Create directories
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)
    
    # Initialize channel manager
    channel_manager = ChannelManager(
        config_file=args.config,
        credentials_dir=args.credentials_dir
    )
    
    # List channels if requested
    if args.list_channels:
        channels = channel_manager.list_channels()
        if not channels:
            logger.info("No channels configured.")
            logger.info("Run with --create-sample-config to create a sample configuration.")
        else:
            logger.info(f"Configured channels ({len(channels)}):")
            for name in channels:
                ch = channel_manager.get_channel(name)
                if ch:
                    logger.info(f"  - {name}: {ch.schedule} ({len(ch.topics)} topics)")
        return
    
    # Check for channels
    if not channel_manager.list_channels():
        logger.warning("No channels configured!")
        logger.info("Creating sample configuration...")
        create_sample_config(args.config)
        channel_manager = ChannelManager(
            config_file=args.config,
            credentials_dir=args.credentials_dir
        )
    
    # Run in one-shot mode
    if args.once or args.mode == 'once':
        if not args.channel:
            # Use first channel if not specified
            channels = channel_manager.list_channels()
            if channels:
                args.channel = channels[0]
                logger.info(f"No channel specified, using: {args.channel}")
            else:
                logger.error("No channels available")
                return
        
        # Choose generation function based on video mode
        video_mode = getattr(args, 'video_mode', 'meme')
        
        # Catch-up logic for delayed runs (1 video per 15 minutes)
        # --------------------------------------------------------
        from app.services.script_cache import get_topic_cache
        from datetime import datetime, timezone
        
        cache = get_topic_cache()
        last_run = cache.get_last_usage_time(args.channel)
        
        num_videos = args.limit
        if args.catchup and last_run:
            # We want to maintain a frequency of 1 video per 15 minutes
            now = datetime.now()
            # Ensure last_run is aware if it's not (TopicCache uses local time)
            elapsed_seconds = (now - last_run).total_seconds()
            
            # If more than 15 minutes have passed, calculate how many videos we "missed"
            # We cap it at the specified limit (default 1) or a reasonable max
            missed_slots = int(elapsed_seconds // (15 * 60))
            if missed_slots > 1:
                # Limit catch-up to maximum 2 videos per run (1 current + 1 catch-up) to avoid spam
                num_videos = min(args.limit if args.limit > 1 else 2, missed_slots)
                logger.info(f"🚀 Catch-up mode: {missed_slots} slots missed since last run ({last_run.strftime('%H:%M')}). Generating {num_videos} videos.")

        total_success = 0
        any_error = False
        for i in range(num_videos):
            if num_videos > 1:
                logger.info(f"📢 Generating catch-up video {i+1}/{num_videos}...")
            
            if video_mode == 'meme':
                result = generate_meme_and_upload(
                    channel_name=args.channel,
                    channel_manager=channel_manager,
                    topic=args.topic,
                    dry_run=args.dry_run,
                    ignore_interval=(num_videos > 1),
                    ignore_schedule=args.ignore_schedule
                )
            else:
                result = generate_and_upload(
                    channel_name=args.channel,
                    channel_manager=channel_manager,
                    topic=args.topic,
                    dry_run=args.dry_run,
                    ignore_interval=(num_videos > 1),
                    ignore_schedule=args.ignore_schedule
                )
            
            if result is True:
                total_success += 1
            elif result is False:
                any_error = True
            
            # Small delay between batch uploads to stabilize YouTube ingestion
            if num_videos > 1 and i < num_videos - 1:
                import time
                time.sleep(10)
        
        # Exit with 0 if no errors occurred (even if skipped)
        # Exit with 1 only if there was a genuine generation/upload failure
        sys.exit(1 if any_error else 0)
    
    # Run scheduler
    if args.mode == 'scheduler':
        run_scheduler(channel_manager, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
