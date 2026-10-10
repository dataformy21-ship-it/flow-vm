from playwright.sync_api import sync_playwright
import requests

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"URL: {page.url}")
    
    # Find all video elements
    videos = page.query_selector_all("video")
    print(f"\nVideos found: {len(videos)}")
    
    for i, v in enumerate(videos):
        try:
            src = v.get_attribute("src")
            print(f"  [{i}] src={src[:100] if src else 'None'}")
        except Exception as e:
            print(f"  [{i}] error: {e}")
    
    # Also look for video URLs in page
    # Try to find download links
    print("\nLooking for download buttons...")
    for txt in ["Download", "download"]:
        els = page.get_by_text(txt, exact=False).all()
        print(f"  '{txt}': {len(els)}")
    
    page.screenshot(path="/tmp/videos_done.png")
    print("\nScreenshot: /tmp/videos_done.png")
