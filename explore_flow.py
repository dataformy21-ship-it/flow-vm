#!/usr/bin/env python3
"""Flow UI Explorer - Find the prompt input and generate button selectors.
Run in Colab with: !python explore_flow.py
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        # Apply patch via route interception
        patched = {"count": 0}

        async def handle_route(route):
            req = route.request
            if "batchexecute" in req.url and "cPZSdc" in req.url:
                resp = await route.fetch()
                body = await resp.text()
                lines = body.split("\n")
                changed = 0
                for i, ln in enumerate(lines):
                    if not ln.startswith("[["):
                        continue
                    try:
                        a = json.loads(ln)
                    except:
                        continue
                    ch = False
                    for k in a:
                        if not isinstance(k, list) or len(k) < 3:
                            continue
                        if k[0] != "wrb.fr" or k[1] != "cPZSdc":
                            continue
                        try:
                            inner = json.loads(k[2])
                        except:
                            continue
                        if not isinstance(inner, list) or len(inner) < 32:
                            continue
                        if inner[30] is not None and not isinstance(inner[30], bool):
                            continue
                        inner[30] = True
                        k[2] = json.dumps(inner)
                        ch = True
                        changed += 1
                    if ch:
                        nl = json.dumps(a)
                        ol = ln[:-1] if ln.endswith("\r") else ln
                        try:
                            pl = int(lines[i-1].strip())
                        except:
                            pl = -1
                        ob = len(ol.encode('utf-8'))
                        nb = len(nl.encode('utf-8'))
                        if 0 <= pl - ob <= 2:
                            lines[i-1] = str(pl + (nb - ob))
                        else:
                            oc = len(ol); nc = len(nl)
                            if 0 <= pl - oc <= 2:
                                lines[i-1] = str(pl + (nc - oc))
                        lines[i] = nl
                if changed > 0:
                    patched["count"] += changed
                    await route.fulfill(response=resp, body="\n".join(lines))
                else:
                    await route.continue_()
            else:
                await route.continue_()

        await context.route("**/*", handle_route)

        print("🌐 Loading Flow...")
        await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(8000)

        url = page.url
        print(f"📍 URL: {url}")
        if "unsupported-country" in url:
            print("❌ Blocked!")
            return

        print(f"🔧 Patches: {patched['count']}")
        print(f"📄 Title: {await page.title()}")
        print()

        # Find text inputs and textareas
        print("=" * 50)
        print("TEXT INPUTS / TEXTAREAS:")
        print("=" * 50)
        inputs = await page.query_selector_all("textarea, input[type='text'], [contenteditable='true']")
        for idx, el in enumerate(inputs):
            try:
                tag = await el.evaluate("e => e.tagName")
                placeholder = await el.get_attribute("placeholder") or ""
                aria = await el.get_attribute("aria-label") or ""
                id_attr = await el.get_attribute("id") or ""
                cls = await el.get_attribute("class") or ""
                visible = await el.is_visible()
                print(f"  [{idx}] {tag} | visible={visible}")
                print(f"       placeholder='{placeholder[:60]}' aria='{aria[:60]}' id='{id_attr[:40]}'")
            except Exception as e:
                print(f"  [{idx}] error: {e}")

        print()
        print("=" * 50)
        print("BUTTONS:")
        print("=" * 50)
        buttons = await page.query_selector_all("button")
        for idx, el in enumerate(buttons[:20]):  # First 20
            try:
                text = (await el.inner_text()).strip()[:50]
                aria = await el.get_attribute("aria-label") or ""
                visible = await el.is_visible()
                print(f"  [{idx}] '{text}' | aria='{aria[:50]}' | visible={visible}")
            except:
                pass

        print()
        print("=" * 50)
        print("Click 'New project' or similar? Looking for navigation...")
        print("=" * 50)
        # Save screenshot
        await page.screenshot(path="/tmp/flow_ui.png")
        print("📸 Screenshot: /tmp/flow_ui.png")

        # Get page HTML snippet for manual inspection
        html = await page.content()
        print(f"📝 HTML length: {len(html)} chars")

asyncio.run(explore())
