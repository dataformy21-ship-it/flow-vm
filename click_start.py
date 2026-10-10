from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"Current URL: {page.url}")
    
    # Find and click "Start Creating"
    btn = page.get_by_text("Start Creating", exact=False).first
    if btn:
        print("Found 'Start Creating', clicking...")
        btn.click()
        page.wait_for_timeout(8000)
        print(f"New URL: {page.url}")
        print(f"Title: {page.title()}")
    else:
        print("Start Creating NOT found")
    
    # Look for text inputs
    inputs = page.query_selector_all("textarea, input[type='text'], [contenteditable='true']")
    print(f"\nTEXT INPUTS: {len(inputs)}")
    for i, inp in enumerate(inputs[:10]):
        tag = inp.evaluate("e => e.tagName")
        ph = inp.get_attribute("placeholder")
        print(f"  [{i}] {tag} placeholder='{ph}'")
    
    # Buttons
    buttons = page.query_selector_all("button")
    print(f"\nBUTTONS: {len(buttons)}")
    for b in buttons[:20]:
        try:
            txt = b.inner_text().strip()[:40]
            if txt:
                print(f"  '{txt}'")
        except:
            pass
    
    page.screenshot(path="/tmp/flow_create.png")
    print("\nScreenshot: /tmp/flow_create.png")
