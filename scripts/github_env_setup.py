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
    print(f"Created {config_file} with video_source: {video_source}")
    
    # 2. Setup YouTube Credentials for the specific channel
    client_secret_content = os.environ.get("CLIENT_SECRET_JSON")
    target_secret_file = credentials_dir / f"{channel_name}_client_secret.json"
    
    if client_secret_content:
        with open(target_secret_file, "w") as f:
            f.write(client_secret_content)
        print(f"Created {target_secret_file} from secret")
    elif target_secret_file.exists():
        print(f"Using existing {target_secret_file} from repository")
    else:
        print(f"WARNING: No client secret found for {channel_name}")
        
    # Setup token: Priority: Google Sheets > Secret > Local File
    token_saved = False
    
    # Try fetching from Google Sheets
    # Try fetching from Google Sheets
    try:
        import sys
        sys.path.insert(0, str(root_dir))
        from app.services.token_storage import TokenStorage
        
        print("Attempting to fetch token from Google Sheets...")
        storage = TokenStorage()
        token_data = storage.get_token(channel_name)
        
        if token_data:
            target_token_file = credentials_dir / f"{channel_name}_token.json"
            with open(target_token_file, "w") as f:
                json.dump(token_data, f)
            print(f"✅ Fetched and saved token for {channel_name} from Google Sheets")
            token_saved = True
        else:
            print("No token found in Google Sheets")
    except ImportError:
        print("TokenStorage service not found (dependencies missing?), skipping Google Sheets fetch.")
    except Exception as e:
        print(f"Failed to fetch from Google Sheets: {e}")

    # Fallback to Secret or Local File
    if not token_saved:
        token_content = os.environ.get("TOKEN_JSON")
        target_token_file = credentials_dir / f"{channel_name}_token.json"
        
        if token_content:
            with open(target_token_file, "w") as f:
                f.write(token_content)
            print(f"Created {target_token_file} from secret")
        elif target_token_file.exists():
            print(f"Using existing {target_token_file} from repository")
        else:
            print(f"WARNING: No token found for {channel_name}")

    # 3. Setup channels.json if passed as secret (optional, otherwise uses repo file)
    channels_content = os.environ.get("CHANNELS_CONFIG")
    if channels_content:
        config_dir = root_dir / "config"
        config_dir.mkdir(exist_ok=True)
        with open(config_dir / "channels.json", "w") as f:
            f.write(channels_content)
        print("Created channels.json from secret")

if __name__ == "__main__":
    setup_environment()
