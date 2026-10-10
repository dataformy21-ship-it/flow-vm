from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"URL: {page.url}")
    
    # Detailed input analysis
    inputs = page.query_selector_all("textarea, input[type='text'], input:not([type]), [contenteditable='true']")
    print(f"\n=== INPUTS ({len(inputs)}) ===")
    for i, inp in enumerate(inputs):
        try:
            tag = inp.evaluate("e => e.tagName")
            ph = inp.get_attribute("placeholder") or ""
            aria = inp.get_attribute("aria-label") or ""
            val = inp.input_value()[:50] if tag in ("INPUT", "TEXTAREA") else ""
            visible = inp.is_visible()
            print(f"  [{i}] {tag} visible={visible} placeholder='{ph}' aria='{aria}' value='{val}'")
        except Exception as e:
            print(f"  [{i}] ERROR: {e}")
    
    # Look for model selector (Veo 3.1 Fast)
    print(f"\n=== MODEL SELECTORS ===")
    for txt in ["Veo", "3.1", "Fast", "Model"]:
        els = page.get_by_text(txt, exact=False).all()
        print(f"  '{txt}': {len(els)} matches")
        for el in els[:3]:
            try:
                t = el.inner_text().strip()[:60]
                print(f"    - '{t}'")
            except:
                pass
    
    # Look for duration settings
    print(f"\n=== DURATION ===")
    for txt in ["10s", "10 sec", "Duration", "seconds"]:
        els = page.get_by_text(txt, exact=False).all()
        if els:
            print(f"  '{txt}': {len(els)} matches")
    
    # Generate button
    print(f"\n=== GENERATE BUTTONS ===")
    for txt in ["Generate", "Create", "Submit"]:
        els = page.get_by_text(txt, exact=False).all()
        print(f"  '{txt}': {len(els)} matches")
    
    page.screenshot(path="/tmp/flow_detail.png")
    print("\nScreenshot: /tmp/flow_detail.png")
