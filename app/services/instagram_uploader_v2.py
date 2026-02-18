"""
Instagram Reels Upload Service (V2 - Playwright Based)

This module provides functionality to upload videos to Instagram Reels 
using Playwright to simulate browser-based uploads, which is more 
resilient to IP-based API blocks.
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger
from playwright.sync_api import sync_playwright

class InstagramBrowserUploader:
    """
    Instagram Reels uploader using Playwright automation.
    """
    
    def __init__(
        self,
        credentials_dir: str = "./credentials",
        channel_name: str = "default",
        headless: bool = True
    ):
        self.credentials_dir = Path(credentials_dir)
        self.channel_name = channel_name
        self.headless = headless
        self.cookies_file = self.credentials_dir / f"{channel_name}_ig_cookies.json"
        self.creds_file = self.credentials_dir / f"{channel_name}_ig_cred.json"

    def _get_credentials(self):
        if not self.creds_file.exists():
            return None, None
        with open(self.creds_file, "r") as f:
            creds = json.load(f)
            return creds.get("username"), creds.get("password")

    def upload_reels(
        self,
        video_path: str,
        caption: str
    ) -> bool:
        """
        Upload a video to Instagram Reels using a browser in a separate process.
        """
        from multiprocessing import Process, Queue
        
        q = Queue()
        p = Process(
            target=_run_instagram_upload, 
            args=(q, video_path, caption, str(self.cookies_file), str(self.creds_file), self.headless)
        )
        p.start()
        p.join(timeout=300)  # 5 minute max
        
        if p.is_alive():
            logger.warning("Instagram upload process timed out after 5 minutes, terminating...")
            p.terminate()
            p.join(timeout=10)
            return False
        
        try:
            result = q.get(timeout=5)
        except Exception:
            logger.error("Instagram upload process returned no result")
            return False
            
        if result is True:
            logger.success("Instagram browser upload completed.")
            return True
        else:
            logger.error(f"Instagram browser upload process failed: {result}")
            return False

def _run_instagram_upload(queue, video_path, caption, cookies_file_path, creds_file_path, headless):
    """Helper function to run Instagram upload in a separate process."""
    from playwright.sync_api import sync_playwright
    import json
    import time
    import os
    from pathlib import Path
    
    video_path = os.path.abspath(video_path)
    
    try:
        with sync_playwright() as p:
            # Stealth args to bypass bot detection
            browser = p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            
            # Load cookies if they exist
            cookies_file = Path(cookies_file_path)
            if cookies_file.exists():
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)

            page = context.new_page()
            
            try:
                # 1. Login Logic — navigate directly to login page to avoid signup redirect
                logger.info("Instagram: Navigating to login page...")
                page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                
                # Take diagnostic screenshot
                page.screenshot(path="storage/ig_after_nav.png")
                
                # Check if we're already logged in (cookies worked)
                current_url = page.url
                logger.info(f"Instagram: Current URL after navigation: {current_url}")
                
                # If redirected to homepage, we're logged in
                already_logged_in = (
                    "instagram.com/" == current_url.rstrip("/") + "/" or
                    current_url.endswith("instagram.com/") or
                    "/accounts/login" not in current_url
                )
                
                if not already_logged_in:
                    # We need to log in
                    logger.info("Instagram: Login required, filling credentials...")
                    
                    # Wait for login form — Instagram uses different field names in different versions
                    username_input = None
                    for field_sel in ['input[name="username"]', 'input[name="email"]', 'input[type="text"]']:
                        try:
                            el = page.locator(field_sel).first
                            if el.is_visible(timeout=5000):
                                username_input = el
                                break
                        except Exception:
                            continue
                    
                    if not username_input:
                        page.screenshot(path="storage/ig_login_fields_not_found.png")
                        queue.put("Could not find login input fields (screenshot: storage/ig_login_fields_not_found.png)")
                        return
                    
                    with open(creds_file_path, "r") as f:
                        creds = json.load(f)
                        username = creds.get("username")
                        password = creds.get("password")
                    
                    if not username or not password:
                        queue.put("Missing credentials")
                        return

                    username_input.fill(username)
                    
                    # Find password field
                    password_input = None
                    for field_sel in ['input[name="password"]', 'input[name="pass"]', 'input[type="password"]']:
                        try:
                            el = page.locator(field_sel).first
                            if el.is_visible(timeout=3000):
                                password_input = el
                                break
                        except Exception:
                            continue
                    
                    if password_input:
                        password_input.fill(password)
                    else:
                        page.screenshot(path="storage/ig_password_not_found.png")
                        queue.put("Could not find password field")
                        return
                    
                    # Click login button via JS to avoid matching "Log in with Facebook"
                    page.evaluate("""() => {
                        // Try submit button first
                        const submit = document.querySelector('button[type="submit"]');
                        if (submit) { submit.click(); return; }
                        // Fallback: find button with exact "Log in" text (not "Log in with Facebook")
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.textContent.trim() === 'Log in') {
                                btn.click();
                                return;
                            }
                        }
                    }""")

                    
                    # Wait for login to complete
                    try:
                        page.wait_for_selector(
                            'svg[aria-label="Direct"], svg[aria-label="New post"], button:has-text("Not Now"), svg[aria-label="Home"]',
                            timeout=30000
                        )
                    except Exception:
                        # May have additional modals or challenges
                        pass
                    
                    time.sleep(3)
                    
                    # Validate post-login URL — check for challenge or signup redirect
                    post_login_url = page.url
                    logger.info(f"Instagram: Post-login URL: {post_login_url}")
                    
                    failed_login_indicators = ['/emailsignup', '/challenge', '/accounts/signup', '/accounts/login']
                    if any(ind in post_login_url for ind in failed_login_indicators):
                        page.screenshot(path="storage/ig_login_failed.png")
                        queue.put(f"Login failed or challenged — ended up at: {post_login_url} (screenshot: storage/ig_login_failed.png)")
                        return
                    
                    # Dismiss "Save Your Login Info?" and "Turn on Notifications" modals
                    for _ in range(3):
                        try:
                            not_now = page.locator('button:has-text("Not Now")').first
                            if not_now.is_visible(timeout=3000):
                                not_now.click()
                                time.sleep(2)
                        except Exception:
                            break

                    # Save cookies for next time
                    cookies = context.cookies()
                    with open(cookies_file, 'w') as f:
                        json.dump(cookies, f)
                    
                    logger.info("Instagram: Login successful, cookies saved.")

                else:
                    logger.info("Instagram: Already logged in via cookies.")

                # 2. Create Post
                time.sleep(3)
                logger.info("Instagram: Searching for 'Create' button...")
                create_selectors = [
                     'svg[aria-label="New post"]',
                     'svg[aria-label="Create"]',
                     'a[href="#"]:has(svg[aria-label="New post"])',
                     'div[role="button"]:has-text("Create")',
                     'span:has-text("Create")',
                     'div[role="menuitem"]:has-text("Post")'
                ]
                
                created = False
                for selector in create_selectors:
                    try:
                        target = page.locator(selector).first
                        if target.is_visible(timeout=5000):
                            target.click()
                            time.sleep(2)
                            # Handle nested Post button in dropdown
                            try:
                                post_item = page.locator('span:has-text("Post"), svg[aria-label="Post"]').first
                                if post_item.is_visible(timeout=3000):
                                    post_item.click()
                            except Exception:
                                pass
                            created = True
                            break
                    except Exception:
                        continue
                
                if not created:
                    page.screenshot(path="storage/ig_create_not_found.png")
                    queue.put("Could not find Create button (screenshot: storage/ig_create_not_found.png)")
                    return
                
                time.sleep(10)
                
                logger.info("Instagram: Uploading file...")
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=60000)
                file_input.set_input_files(video_path)
                time.sleep(10)
                
                # Click through "Next" steps (crop, filters)
                for _ in range(2):
                    try:
                        next_btn = page.get_by_role("button", name="Next")
                        if next_btn.is_visible(timeout=20000):
                            next_btn.click()
                            time.sleep(5)
                    except Exception:
                        pass

                # 3. Caption and Share
                logger.info("Instagram: Writing caption...")
                try:
                    caption_area = page.get_by_role("textbox", name="Write a caption...")
                    caption_area.fill(caption)
                except Exception:
                    # Fallback: try any contenteditable area
                    try:
                        caption_area = page.locator('div[contenteditable="true"]').first
                        caption_area.click()
                        caption_area.fill(caption)
                    except Exception:
                        logger.warning("Instagram: Could not fill caption, continuing without it.")
                
                time.sleep(2)
                
                logger.info("Instagram: Clicking 'Share'...")
                page.get_by_role("button", name="Share").click()
                page.wait_for_selector("text='Your reel has been shared'", timeout=120000)
                
                browser.close()
                queue.put(True)

            except Exception as e:
                page.screenshot(path="storage/ig_upload_exception.png")
                queue.put(f"{str(e)} (screenshot: storage/ig_upload_exception.png)")
                browser.close()
    except Exception as outer_e:
        queue.put(f"Outer process error: {str(outer_e)}")



def upload_to_instagram_browser(
    video_path: str,
    caption: str,
    channel_name: str = "default",
    credentials_dir: str = "./credentials"
) -> bool:
    """Convenience function for Instagram Browser upload."""
    uploader = InstagramBrowserUploader(credentials_dir=credentials_dir, channel_name=channel_name)
    return uploader.upload_reels(video_path=video_path, caption=caption)
