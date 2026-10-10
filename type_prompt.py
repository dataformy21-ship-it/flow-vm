from playwright.sync_api import sync_playwright

PROMPT = "A cute cartoon cat speaking in Myanmar language, saying 'mingalaba', friendly smile, 10 seconds, close-up, no text overlay"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"URL: {page.url}")
    
    # Dismiss any modal with Escape
    print("Pressing Escape to dismiss modals...")
    page.keyboard.press("Escape")
    page.wait_for_timeout(2000)
    page.keyboard.press("Escape")
    page.wait_for_timeout(2000)
    
    # Find the prompt box (ProseMirror)
    prompt_box = page.locator(".prosemirror-placeholder").first
    if not prompt_box.count():
        # Try contenteditable
        prompt_box = page.locator("[contenteditable='true']").first
    
    print(f"Prompt box found: {prompt_box.count() > 0}")
    
    if prompt_box.count():
        print("Clicking prompt box...")
        try:
            prompt_box.click(timeout=10000)
            page.wait_for_timeout(1000)
            print("Typing prompt...")
            page.keyboard.type(PROMPT, delay=10)
            page.wait_for_timeout(2000)
            print(f"Typed: {PROMPT[:50]}...")
        except Exception as e:
            print(f"Error: {e}")
    
    # Look for Generate/Submit button
    print("\nLooking for generate button...")
    for txt in ["Generate", "Create video", "Submit", "->", "Send"]:
        els = page.get_by_text(txt, exact=False).all()
        if els:
            print(f"  '{txt}': {len(els)}")
    
    # Screenshot
    page.screenshot(path="/tmp/flow_prompt.png")
    print("\nScreenshot: /tmp/flow_prompt.png")
    print(f"\nPROMPT USED: {PROMPT}")
