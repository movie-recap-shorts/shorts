import os
import json
import base64
from pathlib import Path
import toml

def setup_environment():
    """
    Setup the environment for GitHub Actions by creating necessary config and credential files
    from environment variables (secrets).
    """
    print("Setting up environment from secrets...")
    
    root_dir = Path(__file__).parent.parent
    credentials_dir = root_dir / "credentials"
    credentials_dir.mkdir(exist_ok=True)
    
    # Get channel name from environment (defaults to movies_en for backward compatibility)
    channel_name = os.environ.get("CHANNEL_NAME", "movies_en")
    print(f"Setting up for channel: {channel_name}")
    
    # 1. Setup config.toml
    config_file = root_dir / "config.toml"
    
    # Determine video source based on available API keys
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "")
    
    # Prefer Pixabay for copyright-free content
    video_source = "pixabay" if pixabay_key else "pexels"
    
    # Create default config structure
    config_data = {
        "app": {
            "llm_provider": "deepseek",
            "deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "deepseek_base_url": "https://api.deepseek.com",
            "deepseek_model_name": "deepseek-chat",
            "pexels_api_keys": [pexels_key] if pexels_key else [],
            "pixabay_api_keys": [pixabay_key] if pixabay_key else [],
            "video_source": video_source,
            "log_level": "INFO"
        },
        "ui": {
            "font_name": "STHeitiMedium.ttc"
        }
    }
    
    with open(config_file, "w") as f:
        toml.dump(config_data, f)
    print(f"Created {config_file.absolute()} with video_source: {video_source}")
    
    # Setup YouTube Credentials: Priority: Google Sheets > Secrets
    credentials_ready = False
    source_info = "None"
    
    sheet_id = os.environ.get("SHEET_ID")
    sheets_creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    
    print(f"DEBUG: SHEET_ID length: {len(sheet_id) if sheet_id else 0}")
    print(f"DEBUG: GOOGLE_SHEETS_CREDENTIALS length: {len(sheets_creds) if sheets_creds else 0}")

    if sheet_id and sheets_creds:
        try:
            import sys
            sys.path.insert(0, str(root_dir))
            from app.services.token_storage import TokenStorage
            
            print(f"🔍 [Sheets] Checking for channel: {channel_name}...")
            storage = TokenStorage()
            token_data, secret_data = storage.get_credentials(channel_name)
            
            if token_data:
                # Save token
                target_token_file = credentials_dir / f"{channel_name}_token.json"
                with open(target_token_file, "w") as f:
                    json.dump(token_data, f)
                
                # Save client secret
                target_secret_file = credentials_dir / f"{channel_name}_client_secret.json"
                if secret_data:
                    with open(target_secret_file, "w") as f:
                        json.dump(secret_data, f)
                    print(f"✅ [Sheets] Fetched both TOKEN and CLIENT_SECRET from Google Sheets.")
                else:
                    client_secret_content = os.environ.get("CLIENT_SECRET_JSON")
                    if client_secret_content:
                        with open(target_secret_file, "w") as f:
                            f.write(client_secret_content)
                        print(f"✅ [Sheets] Fetched TOKEN from Sheets, CLIENT_SECRET from GitHub Secret.")
                    else:
                        print(f"✅ [Sheets] Fetched TOKEN from Sheets (WARNING: No Client Secret found).")

                print(f"   - Token Expiry: {token_data.get('expiry', 'unknown')}")
                print(f"   - Saved to: {target_token_file.absolute()}")
                credentials_ready = True
                source_info = "Google Sheets"
            else:
                print(f"⚠️ [Sheets] No records found in Google Sheet for '{channel_name}'.")
        except Exception as e:
            print(f"❌ [Sheets] Error during fetch: {str(e)}")
            import traceback
            traceback.print_exc()

    # Fallback to Secrets only
    if not credentials_ready:
        print("⚠️ [Fallback] Falling back to GitHub Secrets for all credentials.")
        token_content = os.environ.get("TOKEN_JSON")
        client_secret_content = os.environ.get("CLIENT_SECRET_JSON")
        
        target_token_file = credentials_dir / f"{channel_name}_token.json"
        target_secret_file = credentials_dir / f"{channel_name}_client_secret.json"
        
        if token_content:
            with open(target_token_file, "w") as f:
                f.write(token_content)
            print(f"ℹ️ [Secrets] Using TOKEN_JSON from secret. Saved to: {target_token_file.absolute()}")
            source_info = "GitHub Secret"
            credentials_ready = True
        
        if client_secret_content:
            with open(target_secret_file, "w") as f:
                f.write(client_secret_content)
            print(f"ℹ️ [Secrets] Using CLIENT_SECRET_JSON from secret. Saved to: {target_secret_file.absolute()}")

    print(f"🏁 Environment setup complete. Source: {source_info}")
    
    if not credentials_ready:
        print("❌ CRITICAL ERROR: NO YOUTUBE CREDENTIALS WERE SETUP! Automation will fail.")

    # 3. Setup channels.json if passed as secret
    channels_content = os.environ.get("CHANNELS_CONFIG")
    if channels_content:
        config_dir = root_dir / "config"
        config_dir.mkdir(exist_ok=True)
        with open(config_dir / "channels.json", "w") as f:
            f.write(channels_content)
        print("Created channels.json from secret")

if __name__ == "__main__":
    setup_environment()
