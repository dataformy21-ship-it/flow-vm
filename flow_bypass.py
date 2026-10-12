#!/usr/bin/env python3
"""Flow AI country-block bypass - run in Colab after VNC setup.
Connects to the running Chromium (CDP :9222), installs the
batchexecute response patch, and opens flow.google.com.

Usage: !python3 /tmp/flow_bypass.py
Keep this cell running while using Flow.
"""
import asyncio, json, sys
from urllib.parse import urlparse

# ---- patch spec (verified 2026-10-10) ----
TAG = "wrb.fr"
RPCID = "cPZSdc"
FLAG_INDEX = 30
MIN_LEN = 32
FLOW_ORIGIN = "https://flow.google.com"
FLOW_PATH = "/_/AiSandboxAngularFrontend/data/batchexecute"

def patch_body(text):
    lines = text.split("\n")
    count = 0
    for i, line in enumerate(lines):
        if not line.startswith("[["):
            continue
        try:
            arr = json.loads(line)
        except Exception:
            continue
        changed = False
        for chunk in arr:
            if not (isinstance(chunk, list) and len(chunk) >= 3):
                continue
            if chunk[0] != TAG or chunk[1] != RPCID:
                continue
            try:
                payload = json.loads(chunk[2])
            except Exception:
                continue
            if not isinstance(payload, list) or len(payload) < MIN_LEN:
                continue
            if payload[FLAG_INDEX] is not None and not isinstance(payload[FLAG_INDEX], bool):
                continue
            payload[FLAG_INDEX] = True
            chunk[2] = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            changed = True
            count += 1
        if changed:
            new_line = json.dumps(arr, separators=(",", ":"), ensure_ascii=False)
            old_line = line[:-1] if line.endswith("\r") else line
            prev_len = int(lines[i - 1].strip())
            old_bytes = len(old_line.encode("utf-8"))
            old_chars = len(old_line)
            if prev_len - old_bytes in (0, 1, 2):
                new_enc, base = len(new_line.encode("utf-8")), old_bytes
            elif prev_len - old_chars in (0, 1, 2):
                new_enc, base = len(new_line), old_chars
            else:
                continue
            lines[i - 1] = str(prev_len + (new_enc - base))
            lines[i] = new_line
    return "\n".join(lines), count

async def main():
    from playwright.async_api import async_playwright

    print("🔌 Connecting to Chromium (CDP :9222)...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=15000)
        except Exception as e:
            print(f"❌ Cannot connect to Chromium: {e}")
            print("   Make sure VNC setup is running (restart_vnc.py).")
            sys.exit(1)
        print("✅ Connected to Chromium")

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        patched_total = {"n": 0}

        async def handle_route(route):
            req = route.request
            u = urlparse(req.url)
            if u.hostname == "flow.google.com" and u.path == FLOW_PATH and RPCID in (u.query or ""):
                try:
                    resp = await route.fetch()
                    body = await resp.text()
                    new_body, n = patch_body(body)
                    if n > 0:
                        patched_total["n"] += n
                        print(f"🛡️  Patched {n} config response(s) (total {patched_total['n']})", flush=True)
                        await route.fulfill(response=resp, body=new_body)
                    else:
                        await route.continue_()
                except Exception as e:
                    print(f"⚠️  patch error: {e}", flush=True)
                    await route.continue_()
            else:
                await route.continue_()

        await context.route("**/*", handle_route)
        print("🛡️  Bypass active — batchexecute patch installed")
        print("🌐 Opening flow.google.com ...")
        await page.bring_to_front()
        await page.goto(FLOW_ORIGIN, wait_until="domcontentloaded", timeout=60000)
        print("")
        print("=" * 55)
        print("✅ Flow is open in the VNC Chromium!")
        print("   Go to your VNC desktop → Chrome → flow.google.com")
        print("   The country block should be GONE.")
        print("   Keep this cell RUNNING while using Flow.")
        print("=" * 55)
        # keep alive
        try:
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n🛑 Bypass stopped.")

if __name__ == "__main__":
    asyncio.run(main())
