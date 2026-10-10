from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"URL: {page.url}")
    
    # Verify prompt is there
    editor = page.locator(".prosemirror-editor").first
    try:
        txt = editor.inner_text()[:80]
        print(f"Prompt in box: '{txt}'")
    except:
        print("Could not read editor text")
    
    # Find ALL buttons with their text
    print("\n=== ALL BUTTONS ===")
    buttons = page.query_selector_all("button")
    for i, b in enumerate(buttons):
        try:
            t = b.inner_text().strip()
            aria = b.get_attribute("aria-label") or ""
            vis = b.is_visible()
            if t or aria:
                print(f"  [{i}] '{t[:40]}' aria='{aria[:40]}' visible={vis}")
        except:
            pass
    
    # Look specifically for generate/submit
    print("\n=== GENERATE CANDIDATES ===")
    for sel in ["[aria-label*='Generate']", "[aria-label*='Create']", "button[type='submit']"]:
        els = page.query_selector_all(sel)
        print(f"  {sel}: {len(els)}")
    
    page.screenshot(path="/tmp/flow_ready.png")
    print("\nScreenshot: /tmp/flow_ready.png")
