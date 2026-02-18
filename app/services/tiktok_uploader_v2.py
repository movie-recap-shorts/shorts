"""
TikTok Video Upload Service (V2 - Custom Playwright Based)

This module provides a robust, browser-based TikTok uploader that specifically 
handles the various modals (Copyright, Interactivity, etc.) that TikTok 
presents during the web upload flow.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, List

from loguru import logger
from playwright.sync_api import sync_playwright

class TikTokBrowserUploader:
    """
    TikTok uploader with explicit modal handling and progress tracking.
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
        self.cookies_file = self.credentials_dir / f"{channel_name}_tiktok_cookies.txt"

    def upload_video(
        self,
        video_path: str,
        description: str
    ) -> bool:
        """
        Upload a video to TikTok using a browser in a separate process.
        """
        from multiprocessing import Process, Queue
        
        q = Queue()
        p = Process(
            target=_run_tiktok_upload,
            args=(q, video_path, description, str(self.cookies_file), self.headless)
        )
        p.start()
        p.join(timeout=300)  # 5 minute max
        
        if p.is_alive():
            logger.warning("TikTok upload process timed out after 5 minutes, terminating...")
            p.terminate()
            p.join(timeout=10)
            return False
        
        try:
            result = q.get(timeout=5)
        except Exception:
            logger.error("TikTok upload process returned no result")
            return False
            
        if result is True:
            logger.success("TikTok browser upload completed.")
            return True
        else:
            logger.error(f"TikTok browser upload process failed: {result}")
            return False

def _run_tiktok_upload(queue, video_path, description, cookies_file_path, headless):
    """Helper function to run TikTok upload in a separate process."""
    from playwright.sync_api import sync_playwright
    import json
    import time
    import os
    
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
            
            # Load and normalize cookies
            with open(cookies_file_path, 'r') as f:
                cookies_data = json.load(f)
            
            normalized_cookies = []
            for cookie in cookies_data:
                new_cookie = cookie.copy()
                if 'expirationDate' in cookie:
                    expiry = int(cookie['expirationDate'])
                    new_cookie['expires'] = expiry
                
                if 'sameSite' in cookie:
                    ss = str(cookie['sameSite']).lower()
                    if ss in ['strict', 'lax', 'none']:
                        new_cookie['sameSite'] = ss.capitalize()
                    else:
                        del new_cookie['sameSite']
                normalized_cookies.append(new_cookie)
                
            context.add_cookies(normalized_cookies)

            page = context.new_page()
            
            try:
                logger.info("Navigating to TikTok Upload page...")
                page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded", timeout=90000)
                time.sleep(10)
                
                if "login" in page.url or page.locator('text="Log in"').is_visible(timeout=10000):
                    page.screenshot(path="storage/tt_session_expired.png")
                    queue.put("TikTok session expired (screenshot: storage/tt_session_expired.png)")
                    return

                # 1. Upload File
                logger.info("TikTok: Uploading file...")
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=60000)
                file_input.set_input_files(video_path)
                time.sleep(15)
                
                # Helper: Dismiss any blocking modals via JavaScript
                def dismiss_modal():
                    """Dismiss TikTok's 'automatic content checks' or any other modal."""
                    for _ in range(5):
                        result = page.evaluate("""() => {
                            const portal = document.querySelector('[data-floating-ui-portal]');
                            if (!portal) return 'no_modal';
                            
                            const targetTexts = ['Turn on', 'Cancel', 'Got it', 'OK', 'Not now'];
                            
                            // Strategy 1: Find button/role=button elements with matching text
                            const btns = portal.querySelectorAll('button, [role="button"]');
                            for (const btn of btns) {
                                const t = btn.textContent.trim();
                                for (const target of targetTexts) {
                                    if (t === target) {
                                        const rect = btn.getBoundingClientRect();
                                        const cx = rect.left + rect.width / 2;
                                        const cy = rect.top + rect.height / 2;
                                        const opts = {bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy};
                                        btn.dispatchEvent(new PointerEvent('pointerdown', opts));
                                        btn.dispatchEvent(new MouseEvent('mousedown', opts));
                                        btn.dispatchEvent(new PointerEvent('pointerup', opts));
                                        btn.dispatchEvent(new MouseEvent('mouseup', opts));
                                        btn.dispatchEvent(new MouseEvent('click', opts));
                                        return 'clicked_btn: ' + t;
                                    }
                                }
                            }
                            
                            // Strategy 2: Find ANY element with matching text (regardless of children)
                            const allEls = portal.querySelectorAll('*');
                            for (const target of targetTexts) {
                                for (const el of allEls) {
                                    if (el.textContent.trim() === target && el.offsetParent !== null) {
                                        const clickTarget = el.closest('button, [role="button"]') || el;
                                        const rect = clickTarget.getBoundingClientRect();
                                        const cx = rect.left + rect.width / 2;
                                        const cy = rect.top + rect.height / 2;
                                        const opts = {bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy};
                                        clickTarget.dispatchEvent(new PointerEvent('pointerdown', opts));
                                        clickTarget.dispatchEvent(new MouseEvent('mousedown', opts));
                                        clickTarget.dispatchEvent(new PointerEvent('pointerup', opts));
                                        clickTarget.dispatchEvent(new MouseEvent('mouseup', opts));
                                        clickTarget.dispatchEvent(new MouseEvent('click', opts));
                                        return 'clicked_any: ' + target;
                                    }
                                }
                            }
                            
                            // Strategy 3: Try X close button
                            const closeBtn = portal.querySelector('[class*="close"], [aria-label="Close"]');
                            if (closeBtn) {
                                const target = closeBtn.closest('[class*="close"], [role="button"], button') || closeBtn;
                                target.click();
                                return 'clicked_x_close';
                            }
                            
                            // Debug: report what's in the portal
                            const texts = Array.from(portal.querySelectorAll('*')).map(e => e.tagName + ':' + e.textContent.trim().substring(0, 30)).slice(0, 10);
                            
                            // Nuclear: remove the portal entirely
                            portal.remove();
                            return 'removed_portal|debug:' + texts.join(', ');
                        }""")
                        logger.info(f"TikTok: Modal dismiss result: {result}")
                        if result == 'no_modal':
                            return True
                        time.sleep(2)
                    return False
                
                # Dismiss any modals that appeared after file upload
                dismiss_modal()
                time.sleep(2)
                
                # 2. Description — use JS focus to bypass any remaining overlays
                logger.info("TikTok: Filling description...")
                page.evaluate("""(desc) => {
                    const editor = document.querySelector('div[contenteditable="true"]');
                    if (editor) {
                        editor.focus();
                        editor.textContent = '';
                        document.execCommand('insertText', false, desc);
                    }
                }""", description)

                
                # 3. Wait for video to finish processing (Post button becomes enabled)
                logger.info("TikTok: Waiting for video processing to complete...")
                for wait_attempt in range(12):  # up to 60s
                    btn_state = page.evaluate("""() => {
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            if (btn.textContent.trim() === 'Post') {
                                return btn.disabled ? 'disabled' : 'enabled';
                            }
                        }
                        return 'not_found';
                    }""")
                    logger.info(f"TikTok: Post button state: {btn_state}")
                    if btn_state == 'enabled':
                        break
                    time.sleep(5)
                

                # Post the video — handle TikTok's "automatic content checks" modal
                logger.info("TikTok: Starting post sequence...")
                
                posted = False
                for attempt in range(15):
                    # Step 1: Dismiss any blocking modals first
                    dismiss_modal()
                    time.sleep(1)
                    
                    # Step 2: Try to click the Post button
                    click_result = page.evaluate("""() => {
                        const portal = document.querySelector('[data-floating-ui-portal]');
                        if (portal) return 'modal_still_present';
                        
                        // Try clicking Post button
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            const text = btn.textContent.trim();
                            if (text === 'Post' && btn.offsetParent !== null && !btn.disabled) {
                                const rect = btn.getBoundingClientRect();
                                const cx = rect.left + rect.width / 2;
                                const cy = rect.top + rect.height / 2;
                                const opts = {bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy};
                                
                                btn.dispatchEvent(new PointerEvent('pointerdown', opts));
                                btn.dispatchEvent(new MouseEvent('mousedown', opts));
                                btn.dispatchEvent(new PointerEvent('pointerup', opts));
                                btn.dispatchEvent(new MouseEvent('mouseup', opts));
                                btn.dispatchEvent(new MouseEvent('click', opts));
                                
                                return 'clicked_post';
                            }
                        }
                        
                        return 'post_button_not_found|url:' + window.location.href;
                    }""")
                    
                    logger.info(f"TikTok: Post click result (attempt {attempt+1}): {click_result}")
                    
                    if click_result == 'clicked_post':
                        # Post was clicked — wait for page navigation (real success = URL changes)
                        logger.info("TikTok: Post clicked, waiting for navigation...")
                        time.sleep(12)
                        try:
                            current_url = page.url
                            logger.info(f"TikTok: URL after post click: {current_url}")
                            if '/upload' not in current_url:
                                logger.info("TikTok: Upload success confirmed — left upload page!")
                                posted = True
                                break
                            # Also check for 'Video published' text (strict check)
                            published = page.evaluate("""() => {
                                const body = document.body.textContent;
                                if (body.includes('Video published')) return true;
                                if (body.includes('Your videos are being uploaded')) return true;
                                return false;
                            }""")
                            if published:
                                logger.info("TikTok: 'Video published' text detected!")
                                posted = True
                                break
                        except Exception:
                            pass
                    elif click_result == 'modal_still_present':
                        logger.info("TikTok: Modal still present, retrying dismiss...")
                    else:
                        logger.info(f"TikTok: Post button not found yet, waiting...")
                    
                    time.sleep(5)
                

                if posted:
                    browser.close()

                    queue.put(True)
                else:
                    page.screenshot(path="storage/tt_post_timeout.png")
                    queue.put("Post/modal timeout (screenshot: storage/tt_post_timeout.png)")
                    return

            except Exception as e:
                page.screenshot(path="storage/tt_upload_exception.png")
                queue.put(f"{str(e)} (screenshot: storage/tt_upload_exception.png)")
                browser.close()
    except Exception as outer_e:
        queue.put(f"Outer process error: {str(outer_e)}")



def upload_to_tiktok_browser(
    video_path: str,
    description: str,
    channel_name: str = "default",
    credentials_dir: str = "./credentials"
) -> bool:
    """Convenience function for TikTok Browser upload."""
    uploader = TikTokBrowserUploader(credentials_dir=credentials_dir, channel_name=channel_name)
    return uploader.upload_video(video_path=video_path, description=description)
