from playwright.sync_api import sync_playwright

PROMPT = "A cute cartoon cat speaking in Myanmar language, saying 'mingalaba', friendly smile, 10 seconds, close-up"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0]
    
    print(f"URL: {page.url}")
    
    # Dismiss modals
    page.keyboard.press("Escape")
    page.wait_for_timeout(1500)
    
    # Find the ProseMirror EDITOR (not the placeholder)
    editor = page.locator(".prosemirror-editor").first
    print(f"Editor found: {editor.count() > 0}")
    
    if editor.count():
        print("Clicking editor...")
        try:
            # Use force click to bypass overlay
            editor.click(timeout=8000, force=True)
            page.wait_for_timeout(1000)
            print("Typing...")
            page.keyboard.type(PROMPT, delay=15)
            page.wait_for_timeout(2000)
            print("Done typing!")
        except Exception as e:
            print(f"Click error: {str(e)[:200]}")
            # Fallback: try focusing via JS
            try:
                editor.evaluate("e => e.focus()")
                page.keyboard.type(PROMPT, delay=15)
                print("Typed via focus fallback!")
            except Exception as e2:
                print(f"Fallback error: {str(e2)[:200]}")
    
    # Check if text was entered
    try:
        text = editor.inner_text()
        print(f"\nEditor text now: '{text[:100]}'")
    except:
        pass
    
    page.screenshot(path="/tmp/flow_typed.png")
    print("\nScreenshot: /tmp/flow_typed.png")
