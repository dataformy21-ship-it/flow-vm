from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"URL: {page.url}")
    
    # Find Create buttons
    creates = page.get_by_text("Create", exact=False).all()
    print(f"\nCreate buttons: {len(creates)}")
    for i, c in enumerate(creates):
        try:
            txt = c.inner_text().strip()[:50]
            print(f"  [{i}] '{txt}' visible={c.is_visible()}")
        except:
            pass
    
    # Click the first visible Create
    for c in creates:
        try:
            if c.is_visible():
                print(f"\nClicking: '{c.inner_text().strip()[:50]}'")
                c.click()
                page.wait_for_timeout(5000)
                print(f"New URL: {page.url}")
                break
        except Exception as e:
            print(f"Click failed: {e}")
    
    # Check for prompt input now
    inputs = page.query_selector_all("textarea, [contenteditable='true']")
    print(f"\nPROMPT INPUTS: {len(inputs)}")
    for i, inp in enumerate(inputs):
        try:
            tag = inp.evaluate("e => e.tagName")
            vis = inp.is_visible()
            ph = inp.get_attribute("placeholder") or ""
            print(f"  [{i}] {tag} visible={vis} placeholder='{ph}'")
        except:
            pass
    
    page.screenshot(path="/tmp/flow_after_create.png")
    print("\nScreenshot: /tmp/flow_after_create.png")
