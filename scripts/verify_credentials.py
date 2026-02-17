
import sys
import os
from pathlib import Path
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.instagram_uploader import InstagramUploader, INSTAGRAPI_AVAILABLE
from app.services.tiktok_uploader import TikTokUploader, TIKTOK_UPLOADER_AVAILABLE

def verify_credentials(channel_name="motivation_en", credentials_dir="./credentials"):
    logger.info(f"Verifying credentials for {channel_name} in {credentials_dir}")
    
    # 1. Instagram Verification
    logger.info("Checking Instagram...")
    if not INSTAGRAPI_AVAILABLE:
        logger.error("❌ instagrapi not installed. Cannot upload to Instagram.")
    else:
        try:
            ig_uploader = InstagramUploader(credentials_dir=credentials_dir, channel_name=channel_name)
            if ig_uploader.creds_file.exists():
                logger.success(f"✅ Instagram credential file found: {ig_uploader.creds_file}")
                # Optional: Try authentication (might trigger login challenge/code)
                # logger.info("Attempting Instagram Login (this might take a moment)...")
                # if ig_uploader.authenticate():
                #     logger.success("✅ Instagram Login Successful")
                # else:
                #     logger.error("❌ Instagram Login Failed")
            else:
                logger.error(f"❌ Instagram credential file missing: {ig_uploader.creds_file}")
        except Exception as e:
            logger.error(f"❌ Instagram check failed: {e}")

    # 2. TikTok Verification
    logger.info("\nChecking TikTok...")
    if not TIKTOK_UPLOADER_AVAILABLE:
        logger.error("❌ tiktok-uploader not installed. Cannot upload to TikTok.")
    else:
        try:
            tt_uploader = TikTokUploader(credentials_dir=credentials_dir, channel_name=channel_name)
            if tt_uploader.cookies_file.exists():
                logger.success(f"✅ TikTok cookies file found: {tt_uploader.cookies_file}")
            else:
                logger.error(f"❌ TikTok cookies file missing: {tt_uploader.cookies_file}")
        except Exception as e:
            logger.error(f"❌ TikTok check failed: {e}")

if __name__ == "__main__":
    verify_credentials()
